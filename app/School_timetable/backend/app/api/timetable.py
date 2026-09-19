from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.core.audit import write_audit
from app.core.rbac import assert_school_entity, get_current_user, get_tenant_school_id, require_roles
from app.database import get_db
from app.models.entities import (
    Day,
    Period,
    RoleName,
    Room,
    Section,
    Subject,
    Teacher,
    TeacherAvailability,
    TimetableEntry,
    TimetableStatus,
    TimetableVersion,
    User,
)
from app.schemas import (
    ApplyChangeRequest,
    ConflictItem,
    ConflictResponse,
    EntryOut,
    GenerateRequest,
    GenerateResponse,
    RegenerateRequest,
    SelectVersionRequest,
    ValidateMoveRequest,
    ValidateMoveResponse,
    VersionOut,
)
from app.services.solver import LockedCell, PlacedLesson
from app.services.timetable import (
    entries_as_lessons,
    generate_timetables,
    load_solver_data,
    section_label,
    selected_version,
)
from app.services.validator import move_errors, validate_lessons
from app.services.notifications import notify, notify_teacher_changes

router = APIRouter(prefix="/timetable", tags=["timetable"])
settings = get_settings()
Admin = require_roles(RoleName.SUPER_ADMIN, RoleName.SCHOOL_ADMIN)
Viewer = require_roles(
    RoleName.SUPER_ADMIN,
    RoleName.SCHOOL_ADMIN,
    RoleName.TEACHER,
    RoleName.STUDENT,
    RoleName.PARENT,
)


def _hydrate_entry(e: TimetableEntry) -> EntryOut:
    return EntryOut(
        id=e.id,
        version_id=e.version_id,
        section_id=e.section_id,
        day_id=e.day_id,
        period_id=e.period_id,
        subject_id=e.subject_id,
        teacher_id=e.teacher_id,
        room_id=e.room_id,
        is_free=e.is_free,
        is_locked=e.is_locked,
        notes=e.notes or "",
        subject_name=e.subject.name if e.subject else "",
        subject_short=(e.subject.short_name or e.subject.name) if e.subject else ("Free" if e.is_free else ""),
        teacher_name=e.teacher.name if e.teacher else "",
        room_name=e.room.name if e.room else "",
        section_label=section_label(e.section) if e.section else "",
        day_name=e.day.name if e.day else "",
        period_name=e.period.name if e.period else "",
        period_index=e.period.period_index if e.period else 0,
    )


def _entry_query(db: Session):
    return db.query(TimetableEntry).options(
        joinedload(TimetableEntry.subject),
        joinedload(TimetableEntry.teacher),
        joinedload(TimetableEntry.room),
        joinedload(TimetableEntry.day),
        joinedload(TimetableEntry.period),
        joinedload(TimetableEntry.section).joinedload(Section.school_class),
    )


def _version_or_selected(db: Session, school_id: int, version_id: int | None) -> TimetableVersion:
    if version_id:
        v = db.get(TimetableVersion, version_id)
        assert_school_entity(v, school_id, "Timetable")
        return v
    v = selected_version(db, school_id)
    if v is None:
        v = (
            db.query(TimetableVersion)
            .filter(TimetableVersion.school_id == school_id)
            .order_by(TimetableVersion.id.desc())
            .first()
        )
    if v is None:
        raise HTTPException(404, "No timetable generated yet")
    return v


@router.post("/generate", response_model=GenerateResponse)
def generate(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    limit = body.time_limit_seconds or settings.solver_max_time_seconds
    locked: list[LockedCell] = []
    if body.lock_existing:
        current = selected_version(db, school_id)
        if current:
            data = load_solver_data(db, school_id)
            locked_entries = db.query(TimetableEntry).filter(TimetableEntry.version_id == current.id).all()
            for e in locked_entries:
                if e.is_locked:
                    lessons = entries_as_lessons([e], data)
                    les = lessons[0] if lessons else None
                    locked.append(
                        LockedCell(
                            section_id=e.section_id,
                            day_id=e.day_id,
                            period_id=e.period_id,
                            assignment_id=les.assignment_id if les else None,
                            room_id=e.room_id,
                            is_free=e.is_free,
                        )
                    )
    versions = generate_timetables(
        db,
        school_id,
        alternatives=body.alternatives,
        time_limit=limit,
        version_name=body.version_name,
        locked=locked,
        morning_hard_mode=body.morning_hard_subjects,
    )
    if versions:
        ready = [v for v in versions if v.status == TimetableStatus.READY]
        if ready:
            db.query(TimetableVersion).filter(TimetableVersion.school_id == school_id).update(
                {"is_selected": False}
            )
            best = max(ready, key=lambda v: v.score)
            best.is_selected = True
    write_audit(
        db,
        user,
        "generate_timetable",
        "timetable_version",
        versions[0].id if versions else "",
        {"count": len(versions)},
        school_id,
    )
    db.commit()
    return GenerateResponse(
        versions=versions,
        selected_id=next((v.id for v in versions if v.is_selected), None),
    )


@router.get("", response_model=list[EntryOut])
def get_master(
    version_id: int | None = None,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Viewer),
):
    version = _version_or_selected(db, school_id, version_id)
    rows = _entry_query(db).filter(TimetableEntry.version_id == version.id).all()
    if user.role.name == RoleName.TEACHER and user.teacher:
        rows = [e for e in rows if e.teacher_id == user.teacher.id]
    return [_hydrate_entry(e) for e in rows]


@router.get("/versions", response_model=list[VersionOut])
def list_versions(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    return (
        db.query(TimetableVersion)
        .filter(TimetableVersion.school_id == school_id)
        .order_by(TimetableVersion.id.desc())
        .all()
    )


@router.post("/select")
def select_version(
    body: SelectVersionRequest,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    version = db.get(TimetableVersion, body.version_id)
    assert_school_entity(version, school_id, "Timetable")
    db.query(TimetableVersion).filter(TimetableVersion.school_id == school_id).update({"is_selected": False})
    version.is_selected = True
    version.status = TimetableStatus.PUBLISHED
    write_audit(db, user, "publish_timetable", "timetable_version", version.id, school_id=school_id)
    db.commit()
    return {"ok": True, "version_id": version.id}


@router.get("/class/{section_id}", response_model=list[EntryOut])
def class_timetable(
    section_id: int,
    version_id: int | None = None,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Viewer),
):
    section = db.get(Section, section_id)
    assert_school_entity(section, school_id, "Section")
    version = _version_or_selected(db, school_id, version_id)
    rows = (
        _entry_query(db)
        .filter(TimetableEntry.version_id == version.id, TimetableEntry.section_id == section_id)
        .all()
    )
    return [_hydrate_entry(e) for e in rows]


@router.get("/teacher/{teacher_id}", response_model=list[EntryOut])
def teacher_timetable(
    teacher_id: int,
    version_id: int | None = None,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Viewer),
):
    teacher = db.get(Teacher, teacher_id)
    assert_school_entity(teacher, school_id, "Teacher")
    if user.role.name == RoleName.TEACHER and user.teacher and user.teacher.id != teacher_id:
        raise HTTPException(403, "Teachers may only view their own timetable")
    version = _version_or_selected(db, school_id, version_id)
    rows = (
        _entry_query(db)
        .filter(TimetableEntry.version_id == version.id, TimetableEntry.teacher_id == teacher_id)
        .all()
    )
    return [_hydrate_entry(e) for e in rows]


@router.get("/room/{room_id}", response_model=list[EntryOut])
def room_timetable(
    room_id: int,
    version_id: int | None = None,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Viewer),
):
    room = db.get(Room, room_id)
    assert_school_entity(room, school_id, "Room")
    version = _version_or_selected(db, school_id, version_id)
    rows = (
        _entry_query(db)
        .filter(TimetableEntry.version_id == version.id, TimetableEntry.room_id == room_id)
        .all()
    )
    return [_hydrate_entry(e) for e in rows]


@router.get("/conflicts", response_model=ConflictResponse)
def conflicts(
    version_id: int | None = None,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
):
    version = _version_or_selected(db, school_id, version_id)
    data = load_solver_data(db, school_id)
    entries = db.query(TimetableEntry).filter(TimetableEntry.version_id == version.id).all()
    lessons = entries_as_lessons(entries, data)
    found = validate_lessons(data, lessons)
    # Attach affected entry ids for teacher unavailability
    by_slot = {(e.section_id, e.day_id, e.period_id): e.id for e in entries}
    for c in found:
        ids = c.entity_ids
        if "teacher_id" in ids and "day_id" in ids:
            affected = [
                e.id
                for e in entries
                if e.teacher_id == ids["teacher_id"]
                and e.day_id == ids.get("day_id")
                and (ids.get("period_id") in (None, e.period_id))
            ]
            c.affected_entry_ids = affected
    hard = sum(1 for c in found if c.type == "hard")
    soft = sum(1 for c in found if c.type == "soft")
    return ConflictResponse(conflicts=found, hard_conflicts=hard, soft_conflicts=soft)


@router.post("/validate", response_model=ValidateMoveResponse)
def validate_move(
    body: ValidateMoveRequest,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    entry = db.get(TimetableEntry, body.entry_id)
    assert_school_entity(entry, school_id, "Entry")
    data = load_solver_data(db, school_id)
    entries = db.query(TimetableEntry).filter(TimetableEntry.version_id == entry.version_id).all()
    lessons = entries_as_lessons(entries, data)
    moving = next(l for l, e in zip(lessons, entries) if e.id == entry.id)
    swap_les = None
    if body.swap_entry_id:
        swap_e = db.get(TimetableEntry, body.swap_entry_id)
        swap_les = next(l for l, e in zip(lessons, entries) if e.id == swap_e.id)
    errors = move_errors(data, lessons, moving, body.target_day_id, body.target_period_id, swap_les)
    if not errors:
        # extra human-readable teacher message
        pass
    pretty = []
    for err in errors:
        if "already teaching" in err.lower() and entry.teacher:
            pretty.append(
                f"Cannot move {entry.subject.name if entry.subject else 'lesson'} "
                f"because {entry.teacher.name} is already teaching another class."
            )
        else:
            pretty.append(err)
    return ValidateMoveResponse(valid=len(errors) == 0, errors=pretty or errors)


@router.post("/apply-change", response_model=EntryOut)
def apply_change(
    body: ApplyChangeRequest,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    entry = db.get(TimetableEntry, body.entry_id)
    assert_school_entity(entry, school_id, "Entry")
    data = load_solver_data(db, school_id)
    entries = db.query(TimetableEntry).filter(TimetableEntry.version_id == entry.version_id).all()
    occupant = next(
        (
            e
            for e in entries
            if e.section_id == entry.section_id
            and e.day_id == body.day_id
            and e.period_id == body.period_id
            and e.id != entry.id
        ),
        None,
    )
    lessons = entries_as_lessons(entries, data)
    moving = next(l for l, e in zip(lessons, entries) if e.id == entry.id)
    swap_les = None
    if occupant:
        swap_les = next(l for l, e in zip(lessons, entries) if e.id == occupant.id)
    errors = move_errors(data, lessons, moving, body.day_id, body.period_id, swap_les)
    if errors:
        raise HTTPException(409, "; ".join(errors))

    old_day, old_period = entry.day_id, entry.period_id
    if occupant:
        occupant.day_id, occupant.period_id = old_day, old_period
    entry.day_id = body.day_id
    entry.period_id = body.period_id
    if body.subject_id is not None:
        entry.subject_id = body.subject_id
    if body.teacher_id is not None:
        entry.teacher_id = body.teacher_id
    if body.room_id is not None:
        entry.room_id = body.room_id
    entry.is_free = body.is_free

    write_audit(
        db,
        user,
        "apply_change",
        "timetable_entry",
        entry.id,
        {"from": [old_day, old_period], "to": [body.day_id, body.period_id]},
        school_id,
    )
    if entry.teacher_id:
        notify_teacher_changes(
            db,
            school_id,
            entry.teacher_id,
            "Timetable change",
            f"A period was moved for {entry.teacher.name if entry.teacher else 'you'}.",
            {"entry_id": entry.id},
        )
    db.commit()
    entry = _entry_query(db).filter(TimetableEntry.id == entry.id).first()
    return _hydrate_entry(entry)


@router.post("/regenerate", response_model=GenerateResponse)
def regenerate(
    body: RegenerateRequest,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    current = selected_version(db, school_id)
    if current is None:
        raise HTTPException(404, "No selected timetable to patch")
    data = load_solver_data(db, school_id)
    entries = db.query(TimetableEntry).filter(TimetableEntry.version_id == current.id).all()
    affected_ids = set(body.affected_entry_ids)
    if body.teacher_id:
        for e in entries:
            if e.teacher_id == body.teacher_id:
                affected_ids.add(e.id)
    locked: list[LockedCell] = []
    for e in entries:
        if e.id in affected_ids:
            continue
        les = entries_as_lessons([e], data)[0]
        locked.append(
            LockedCell(
                section_id=e.section_id,
                day_id=e.day_id,
                period_id=e.period_id,
                assignment_id=les.assignment_id,
                room_id=e.room_id,
                is_free=e.is_free,
            )
        )
    versions = generate_timetables(
        db,
        school_id,
        alternatives=1,
        time_limit=settings.solver_max_time_seconds,
        version_name="Auto-fix",
        locked=locked,
        parent_id=current.id,
    )
    if versions and versions[0].status == TimetableStatus.READY:
        db.query(TimetableVersion).filter(TimetableVersion.school_id == school_id).update(
            {"is_selected": False}
        )
        versions[0].is_selected = True
        versions[0].status = TimetableStatus.PUBLISHED
    write_audit(
        db,
        user,
        "regenerate_partial",
        "timetable_version",
        versions[0].id if versions else "",
        {"affected": list(affected_ids), "reason": body.reason},
        school_id,
    )
    db.commit()
    return GenerateResponse(
        versions=versions,
        selected_id=versions[0].id if versions else None,
    )
