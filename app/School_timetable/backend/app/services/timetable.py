"""Load school data into SolverData and persist solver output."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.models.entities import (
    Day,
    Period,
    Room,
    RoomAvailability,
    SchedulingRule,
    SchoolClass,
    Section,
    Subject,
    SubjectRequirement,
    Teacher,
    TeacherAvailability,
    TeacherClassAssignment,
    TimetableEntry,
    TimetableStatus,
    TimetableVersion,
)
from app.services.solver import (
    AssignmentInfo,
    LockedCell,
    PlacedLesson,
    RoomInfo,
    RuleInfo,
    SolverData,
    TeacherInfo,
    TimetableSolver,
)
from app.services.validator import validate_lessons


def section_label(section: Section) -> str:
    class_name = section.school_class.name if section.school_class else ""
    return section.display_name or f"{class_name}{section.name}"


def load_solver_data(db: Session, school_id: int, locked: list[LockedCell] | None = None) -> SolverData:
    days = db.query(Day).filter(Day.school_id == school_id).order_by(Day.weekday).all()
    periods = db.query(Period).filter(Period.school_id == school_id).order_by(Period.period_index).all()
    sections = (
        db.query(Section)
        .options(joinedload(Section.school_class))
        .filter(Section.school_id == school_id)
        .all()
    )
    teachers = db.query(Teacher).filter(Teacher.school_id == school_id).all()
    rooms = db.query(Room).filter(Room.school_id == school_id, Room.is_active.is_(True)).all()
    assignments = (
        db.query(TeacherClassAssignment)
        .options(
            joinedload(TeacherClassAssignment.teacher),
            joinedload(TeacherClassAssignment.subject),
            joinedload(TeacherClassAssignment.section).joinedload(Section.school_class),
        )
        .filter(TeacherClassAssignment.school_id == school_id)
        .all()
    )
    reqs = db.query(SubjectRequirement).filter(SubjectRequirement.school_id == school_id).all()
    req_map = {(r.section_id, r.subject_id): r.weekly_periods for r in reqs}
    req_pref = {(r.section_id, r.subject_id): r.preferred_periods or [] for r in reqs}
    rules = (
        db.query(SchedulingRule)
        .filter(SchedulingRule.school_id == school_id, SchedulingRule.is_active.is_(True))
        .all()
    )
    t_unavail = db.query(TeacherAvailability).filter(
        TeacherAvailability.school_id == school_id,
        TeacherAvailability.is_available.is_(False),
    ).all()
    r_unavail = db.query(RoomAvailability).filter(
        RoomAvailability.school_id == school_id,
        RoomAvailability.is_available.is_(False),
    ).all()

    assign_infos = []
    for a in assignments:
        subj: Subject = a.subject
        weekly = a.weekly_periods or req_map.get((a.section_id, a.subject_id)) or subj.weekly_required_periods
        prefs = list(subj.preferred_periods or []) + list(req_pref.get((a.section_id, a.subject_id), []))
        assign_infos.append(
            AssignmentInfo(
                id=a.id,
                teacher_id=a.teacher_id,
                section_id=a.section_id,
                subject_id=a.subject_id,
                weekly=int(weekly),
                subject_name=subj.name,
                teacher_name=a.teacher.name,
                is_difficult=bool(subj.is_difficult) or subj.priority >= 8,
                can_be_consecutive=bool(subj.can_be_consecutive),
                preferred_periods=prefs,
                requires_room=bool(subj.requires_room),
                required_room_type=subj.required_room_type.value if subj.required_room_type else None,
                priority=subj.priority,
                subject_type=subj.subject_type.value,
            )
        )

    return SolverData(
        sections=[
            {"id": s.id, "label": section_label(s), "class_id": s.class_id, "room_id": s.room_id}
            for s in sections
        ],
        days=[{"id": d.id, "name": d.name, "weekday": d.weekday, "is_working": d.is_working} for d in days],
        periods=[
            {
                "id": p.id,
                "name": p.name,
                "period_index": p.period_index,
                "is_break": p.is_break,
                "is_free_slot": p.is_free_slot,
            }
            for p in periods
        ],
        assignments=assign_infos,
        teachers=[
            TeacherInfo(
                id=t.id,
                name=t.name,
                max_day=t.max_periods_day,
                max_week=t.max_periods_week,
                min_day=t.min_periods_day,
                preferred_periods=t.preferred_periods or [],
            )
            for t in teachers
        ],
        rooms=[
            RoomInfo(
                id=r.id,
                name=r.name,
                room_type=r.room_type.value,
                allowed_subject_ids=r.allowed_subject_ids or [],
                capacity=r.capacity,
            )
            for r in rooms
        ],
        rules=[
            RuleInfo(
                constraint_type=r.constraint_type,
                payload=r.payload or {},
                weight=r.weight,
                kind=r.kind.value,
            )
            for r in rules
        ],
        teacher_unavailable={(u.teacher_id, u.day_id, u.period_id) for u in t_unavail},
        room_unavailable={(u.room_id, u.day_id, u.period_id) for u in r_unavail},
        locked=locked or [],
        default_weights={r.constraint_type: r.weight for r in rules if r.kind.value == "soft"},
    )


def persist_solution(
    db: Session,
    school_id: int,
    name: str,
    solution,
    academic_year_id: int | None = None,
    parent_id: int | None = None,
) -> TimetableVersion:
    version = TimetableVersion(
        school_id=school_id,
        academic_year_id=academic_year_id,
        name=name,
        status=TimetableStatus.READY if solution.feasible else TimetableStatus.CONFLICTED,
        score=solution.score,
        score_breakdown=solution.score_breakdown,
        constraint_stats=solution.constraint_stats,
        warnings=solution.warnings,
        unsatisfied_preferences=solution.unsatisfied_preferences,
        generation_time_ms=solution.generation_time_ms,
        is_selected=False,
        parent_version_id=parent_id,
        solver_notes=solution.status,
    )
    db.add(version)
    db.flush()
    for les in solution.lessons:
        db.add(
            TimetableEntry(
                school_id=school_id,
                version_id=version.id,
                section_id=les.section_id,
                day_id=les.day_id,
                period_id=les.period_id,
                subject_id=les.subject_id,
                teacher_id=les.teacher_id,
                room_id=les.room_id,
                is_free=les.is_free,
            )
        )
    db.flush()
    return version


def selected_version(db: Session, school_id: int) -> TimetableVersion | None:
    return (
        db.query(TimetableVersion)
        .filter(TimetableVersion.school_id == school_id, TimetableVersion.is_selected.is_(True))
        .order_by(TimetableVersion.id.desc())
        .first()
    )


def generate_timetables(
    db: Session,
    school_id: int,
    alternatives: int,
    time_limit: int,
    version_name: str | None = None,
    locked: list[LockedCell] | None = None,
    parent_id: int | None = None,
    morning_hard_mode: str = "prefer",
) -> list[TimetableVersion]:
    data = load_solver_data(db, school_id, locked=locked)
    data.morning_hard_mode = morning_hard_mode if morning_hard_mode in {"prefer", "require", "anytime"} else "prefer"
    solver = TimetableSolver(max_time_seconds=time_limit)
    solutions = solver.solve_many(data, alternatives=alternatives)
    versions = []
    for i, sol in enumerate(solutions, start=1):
        # Independent validation
        if sol.feasible:
            hard = [c for c in validate_lessons(data, sol.lessons) if c.type == "hard"]
            if hard:
                sol.feasible = False
                sol.warnings = sol.warnings + [c.message for c in hard]
                sol.constraint_stats = {**sol.constraint_stats, "validation_hard": len(hard)}
        name = version_name or f"Solution {i}"
        if alternatives > 1:
            name = f"{name} · {sol.score:.0f}%"
        versions.append(persist_solution(db, school_id, name, sol, parent_id=parent_id))
    return versions


def entries_as_lessons(entries: list[TimetableEntry], data: SolverData) -> list[PlacedLesson]:
    assign_lookup = {
        (a.section_id, a.subject_id, a.teacher_id): a.id for a in data.assignments
    }
    lessons = []
    for e in entries:
        aid = None
        if e.subject_id and e.teacher_id:
            aid = assign_lookup.get((e.section_id, e.subject_id, e.teacher_id))
        lessons.append(
            PlacedLesson(
                section_id=e.section_id,
                day_id=e.day_id,
                period_id=e.period_id,
                assignment_id=aid,
                subject_id=e.subject_id,
                teacher_id=e.teacher_id,
                room_id=e.room_id,
                is_free=e.is_free,
            )
        )
    return lessons


def entity_catalog(db: Session, school_id: int) -> dict:
    teachers = db.query(Teacher).filter(Teacher.school_id == school_id).all()
    subjects = db.query(Subject).filter(Subject.school_id == school_id).all()
    sections = (
        db.query(Section)
        .options(joinedload(Section.school_class))
        .filter(Section.school_id == school_id)
        .all()
    )
    days = db.query(Day).filter(Day.school_id == school_id).all()
    periods = db.query(Period).filter(Period.school_id == school_id).all()
    classes = db.query(SchoolClass).filter(SchoolClass.school_id == school_id).all()
    rooms = db.query(Room).filter(Room.school_id == school_id).all()
    return {
        "teachers": [{"id": t.id, "name": t.name, "employee_id": t.employee_id} for t in teachers],
        "subjects": [{"id": s.id, "name": s.name, "short_name": s.short_name, "code": s.code} for s in subjects],
        "classes": [{"id": c.id, "name": c.name} for c in classes],
        "sections": [{"id": s.id, "label": section_label(s), "class_id": s.class_id} for s in sections],
        "days": [{"id": d.id, "name": d.name, "weekday": d.weekday} for d in days],
        "periods": [
            {"id": p.id, "name": p.name, "period_index": p.period_index, "is_break": p.is_break}
            for p in periods
        ],
        "rooms": [{"id": r.id, "name": r.name, "type": r.room_type.value} for r in rooms],
    }


def resolve_names(db: Session, school_id: int, teacher: str | None = None, day: str | None = None):
    t = None
    d = None
    if teacher:
        t = (
            db.query(Teacher)
            .filter(Teacher.school_id == school_id, Teacher.name.ilike(f"%{teacher}%"))
            .first()
        )
    if day:
        d = db.query(Day).filter(Day.school_id == school_id, Day.name.ilike(f"%{day}%")).first()
    return t, d
