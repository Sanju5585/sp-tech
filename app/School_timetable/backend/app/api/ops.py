from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import get_current_user, get_tenant_school_id, require_roles
from app.database import get_db
from app.models.entities import (
    Day,
    Notification,
    Period,
    RoleName,
    Room,
    SchoolClass,
    Section,
    Subject,
    Teacher,
    TimetableEntry,
    User,
)
from app.schemas import DashboardOut, NotificationOut
from app.services.export import excel_sheets, excel_timetable, pdf_sheets, pdf_timetable
from app.services.timetable import load_solver_data, section_label, selected_version
from app.services.validator import validate_lessons
from app.services.timetable import entries_as_lessons

router = APIRouter(tags=["ops"])
Viewer = require_roles(
    RoleName.SUPER_ADMIN, RoleName.SCHOOL_ADMIN, RoleName.TEACHER, RoleName.STUDENT, RoleName.PARENT
)


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    version = selected_version(db, school_id)
    hard = 0
    score = 0.0
    status = "not_generated"
    last = None
    workload = []
    if version:
        status = version.status.value
        last = version.updated_at
        score = version.score
        data = load_solver_data(db, school_id)
        entries = db.query(TimetableEntry).filter(TimetableEntry.version_id == version.id).all()
        conflicts = validate_lessons(data, entries_as_lessons(entries, data))
        hard = sum(1 for c in conflicts if c.type == "hard")
        by_teacher = defaultdict(int)
        for e in entries:
            if e.teacher_id and not e.is_free:
                by_teacher[e.teacher_id] += 1
        teachers = db.query(Teacher).filter(Teacher.school_id == school_id).all()
        tmap = {t.id: t for t in teachers}
        workload = [
            {
                "teacher_id": tid,
                "name": tmap[tid].name if tid in tmap else str(tid),
                "periods": count,
                "max_week": tmap[tid].max_periods_week if tid in tmap else 0,
            }
            for tid, count in sorted(by_teacher.items(), key=lambda x: -x[1])
        ]
    return DashboardOut(
        total_classes=db.query(SchoolClass).filter(SchoolClass.school_id == school_id).count(),
        total_sections=db.query(Section).filter(Section.school_id == school_id).count(),
        total_teachers=db.query(Teacher).filter(Teacher.school_id == school_id).count(),
        total_subjects=db.query(Subject).filter(Subject.school_id == school_id).count(),
        total_rooms=db.query(Room).filter(Room.school_id == school_id).count(),
        timetable_status=status,
        last_generated=last,
        hard_conflicts=hard,
        soft_preference_score=score,
        teacher_workload=workload,
        selected_version_id=version.id if version else None,
    )


@router.get("/teacher-dashboard")
def teacher_dashboard(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(get_current_user),
):
    if user.role.name != RoleName.TEACHER or not user.teacher:
        raise HTTPException(403, "Teacher dashboard is for teacher accounts")
    teacher = user.teacher
    version = selected_version(db, school_id)
    weekday = date.today().weekday()
    day = db.query(Day).filter(Day.school_id == school_id, Day.weekday == weekday).first()
    entries = []
    if version:
        q = (
            db.query(TimetableEntry)
            .options(
                joinedload(TimetableEntry.subject),
                joinedload(TimetableEntry.section).joinedload(Section.school_class),
                joinedload(TimetableEntry.period),
                joinedload(TimetableEntry.room),
                joinedload(TimetableEntry.day),
            )
            .filter(TimetableEntry.version_id == version.id, TimetableEntry.teacher_id == teacher.id)
        )
        entries = q.all()
    today = [e for e in entries if day and e.day_id == day.id and not e.is_free]
    today.sort(key=lambda e: e.period.period_index if e.period else 0)
    teaching_periods = (
        db.query(Period)
        .filter(Period.school_id == school_id, Period.is_break.is_(False))
        .order_by(Period.period_index)
        .all()
    )
    taught_ids = {e.period_id for e in today}
    free_today = [p.name for p in teaching_periods if p.id not in taught_ids]
    notes = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.id.desc())
        .limit(8)
        .all()
    )
    next_class = None
    if today:
        first = today[0]
        next_class = {
            "subject": first.subject.name if first.subject else "",
            "section": section_label(first.section) if first.section else "",
            "period": first.period.name if first.period else "",
            "room": first.room.name if first.room else "",
        }
    return {
        "teacher_name": teacher.name,
        "today": [
            {
                "period": e.period.name if e.period else "",
                "subject": e.subject.name if e.subject else "",
                "section": section_label(e.section) if e.section else "",
                "room": e.room.name if e.room else "",
            }
            for e in today
        ],
        "next_class": next_class,
        "free_periods": free_today,
        "recent_changes": [{"title": n.title, "body": n.body} for n in notes],
    }


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.id.desc())
        .limit(50)
        .all()
    )


@router.post("/notifications/{nid}/read")
def mark_read(nid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.get(Notification, nid)
    if n is None or n.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    n.is_read = True
    db.commit()
    return {"ok": True}


def _entry_label(e: TimetableEntry, include_class: bool = False) -> str:
    if e.is_free or not e.subject:
        return "Free"
    subject = e.subject.short_name or e.subject.name
    teacher = e.teacher.name if e.teacher else ""
    room = e.room.name if e.room else ""
    klass = section_label(e.section) if include_class and e.section else ""
    lines = [part for part in (klass, subject, teacher, room) if part]
    return "\n".join(lines)


def _export_context(db: Session, school_id: int, version_id: int):
    days = (
        db.query(Day)
        .filter(Day.school_id == school_id, Day.is_working.is_(True))
        .order_by(Day.weekday)
        .all()
    )
    periods = db.query(Period).filter(Period.school_id == school_id).order_by(Period.period_index).all()
    entries = (
        db.query(TimetableEntry)
        .options(
            joinedload(TimetableEntry.subject),
            joinedload(TimetableEntry.teacher),
            joinedload(TimetableEntry.room),
            joinedload(TimetableEntry.section).joinedload(Section.school_class),
        )
        .filter(TimetableEntry.version_id == version_id)
        .all()
    )
    return days, periods, entries


def _class_sheets(days, periods, entries):
    by_section: dict[int, dict] = defaultdict(dict)
    labels: dict[int, str] = {}
    for e in entries:
        labels[e.section_id] = section_label(e.section) if e.section else str(e.section_id)
        by_section[e.section_id][(e.day_id, e.period_id)] = _entry_label(e)
    sheets = []
    for sid, label in sorted(labels.items(), key=lambda item: item[1]):
        grid = by_section[sid]
        sheets.append((f"Class {label}", days, periods, lambda d, p, g=grid: g.get((d, p), "")))
    return sheets


@router.get("/export/pdf")
def export_pdf(
    view: str = "master",
    section_id: int | None = None,
    teacher_id: int | None = None,
    room_id: int | None = None,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Viewer),
):
    version = selected_version(db, school_id)
    if version is None:
        raise HTTPException(404, "No timetable")
    days, periods, entries = _export_context(db, school_id, version.id)
    subtitle = f"{version.name} · hard constraints met · preference score {version.score:.0f}%"
    filename = "timetable.pdf"

    if view == "class" and section_id:
        entries = [e for e in entries if e.section_id == section_id]
        sec = db.get(Section, section_id)
        title = f"Class {section_label(sec)}"
        grid = {(e.day_id, e.period_id): _entry_label(e) for e in entries}
        pdf = pdf_timetable(title, subtitle, days, periods, lambda d, p: grid.get((d, p), ""))
        filename = f"{title}.pdf"
    elif view == "teacher" and teacher_id:
        entries = [e for e in entries if e.teacher_id == teacher_id]
        t = db.get(Teacher, teacher_id)
        title = f"Teacher {t.name if t else teacher_id}"
        grid = {(e.day_id, e.period_id): _entry_label(e, include_class=True) for e in entries}
        pdf = pdf_timetable(title, subtitle, days, periods, lambda d, p: grid.get((d, p), ""))
        filename = f"{title}.pdf"
    elif view == "room" and room_id:
        entries = [e for e in entries if e.room_id == room_id]
        r = db.get(Room, room_id)
        title = f"Room {r.name if r else room_id}"
        grid = {(e.day_id, e.period_id): _entry_label(e, include_class=True) for e in entries}
        pdf = pdf_timetable(title, subtitle, days, periods, lambda d, p: grid.get((d, p), ""))
        filename = f"{title}.pdf"
    else:
        sheets = _class_sheets(days, periods, entries)
        if not sheets:
            raise HTTPException(404, "No timetable entries")
        pdf = pdf_sheets("Class timetables", subtitle, sheets)
        filename = "class-timetables.pdf"

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/excel")
def export_excel(
    view: str = "master",
    section_id: int | None = None,
    teacher_id: int | None = None,
    room_id: int | None = None,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Viewer),
):
    version = selected_version(db, school_id)
    if version is None:
        raise HTTPException(404, "No timetable")
    days, periods, entries = _export_context(db, school_id, version.id)
    filename = "timetable.xlsx"

    if view == "class" and section_id:
        entries = [e for e in entries if e.section_id == section_id]
        sec = db.get(Section, section_id)
        title = f"Class {section_label(sec)}"
        grid = {(e.day_id, e.period_id): _entry_label(e) for e in entries}
        xls = excel_timetable(title, days, periods, lambda d, p: grid.get((d, p), ""))
        filename = f"{title}.xlsx"
    elif view == "teacher" and teacher_id:
        entries = [e for e in entries if e.teacher_id == teacher_id]
        t = db.get(Teacher, teacher_id)
        title = f"Teacher {t.name if t else teacher_id}"
        grid = {(e.day_id, e.period_id): _entry_label(e, include_class=True) for e in entries}
        xls = excel_timetable(title, days, periods, lambda d, p: grid.get((d, p), ""))
        filename = f"{title}.xlsx"
    elif view == "room" and room_id:
        entries = [e for e in entries if e.room_id == room_id]
        r = db.get(Room, room_id)
        title = f"Room {r.name if r else room_id}"
        grid = {(e.day_id, e.period_id): _entry_label(e, include_class=True) for e in entries}
        xls = excel_timetable(title, days, periods, lambda d, p: grid.get((d, p), ""))
        filename = f"{title}.xlsx"
    else:
        sheets = _class_sheets(days, periods, entries)
        if not sheets:
            raise HTTPException(404, "No timetable entries")
        xls = excel_sheets(sheets)
        filename = "class-timetables.xlsx"

    return Response(
        content=xls,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
