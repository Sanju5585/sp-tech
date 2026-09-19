from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.accounts import maybe_create_teacher_login
from app.core.audit import write_audit
from app.core.rbac import assert_school_entity, get_tenant_school_id, require_roles
from app.database import get_db
from app.models.entities import (
    RoleName,
    School,
    SchoolClass,
    Section,
    Teacher,
    TeacherAvailability,
    TeacherClassAssignment,
    TeacherSubject,
    User,
)
from app.schemas import (
    AssignmentIn,
    AssignmentOut,
    AvailabilityIn,
    ClassIn,
    ClassOut,
    ClassUpdate,
    SectionIn,
    SectionOut,
    TeacherAvailabilityOut,
    TeacherIn,
    TeacherOut,
)
from app.services.timetable import section_label

router = APIRouter(tags=["academic"])
Admin = require_roles(RoleName.SUPER_ADMIN, RoleName.SCHOOL_ADMIN)


def _teacher_out(t: Teacher) -> TeacherOut:
    return TeacherOut(
        id=t.id,
        school_id=t.school_id,
        name=t.name,
        employee_id=t.employee_id,
        email=t.email,
        phone=t.phone,
        max_periods_day=t.max_periods_day,
        max_periods_week=t.max_periods_week,
        min_periods_day=t.min_periods_day,
        preferred_periods=t.preferred_periods or [],
        subject_ids=[s.subject_id for s in t.subjects],
        user_id=t.user_id,
    )


def _class_out(c: SchoolClass) -> ClassOut:
    return ClassOut(
        id=c.id,
        school_id=c.school_id,
        name=c.name,
        grade_level=c.grade_level,
        sections=[
            SectionOut(
                id=s.id,
                school_id=s.school_id,
                class_id=s.class_id,
                name=s.name,
                display_name=s.display_name,
                room_id=s.room_id,
                label=section_label(s),
            )
            for s in c.sections
        ],
    )


@router.get("/classes", response_model=list[ClassOut])
def list_classes(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    rows = (
        db.query(SchoolClass)
        .options(joinedload(SchoolClass.sections).joinedload(Section.school_class))
        .filter(SchoolClass.school_id == school_id)
        .all()
    )
    return [_class_out(c) for c in rows]


@router.post("/classes", response_model=ClassOut)
def create_class(
    body: ClassIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = SchoolClass(school_id=school_id, name=body.name, grade_level=body.grade_level)
    db.add(row)
    db.flush()
    for name in body.sections:
        db.add(
            Section(
                school_id=school_id,
                class_id=row.id,
                name=name,
                display_name=f"{body.name}{name}",
            )
        )
    db.commit()
    row = db.get(
        SchoolClass,
        row.id,
        options=[joinedload(SchoolClass.sections).joinedload(Section.school_class)],
    )
    return _class_out(row)


@router.put("/classes/{class_id}", response_model=ClassOut)
def update_class(
    class_id: int,
    body: ClassUpdate,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(SchoolClass, class_id)
    assert_school_entity(row, school_id, "Class")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    row = db.get(
        SchoolClass,
        row.id,
        options=[joinedload(SchoolClass.sections).joinedload(Section.school_class)],
    )
    return _class_out(row)


@router.delete("/classes/{class_id}")
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(SchoolClass, class_id)
    assert_school_entity(row, school_id, "Class")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/sections", response_model=list[SectionOut])
def list_sections(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    rows = (
        db.query(Section)
        .options(joinedload(Section.school_class))
        .filter(Section.school_id == school_id)
        .all()
    )
    return [
        SectionOut(
            id=s.id,
            school_id=s.school_id,
            class_id=s.class_id,
            name=s.name,
            display_name=s.display_name,
            room_id=s.room_id,
            label=section_label(s),
        )
        for s in rows
    ]


@router.post("/sections", response_model=SectionOut)
def create_section(
    body: SectionIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    cls = db.get(SchoolClass, body.class_id)
    assert_school_entity(cls, school_id, "Class")
    row = Section(
        school_id=school_id,
        class_id=body.class_id,
        name=body.name,
        display_name=body.display_name or f"{cls.name}{body.name}",
        room_id=body.room_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row.school_class = cls
    return SectionOut(
        id=row.id,
        school_id=row.school_id,
        class_id=row.class_id,
        name=row.name,
        display_name=row.display_name,
        room_id=row.room_id,
        label=section_label(row),
    )


@router.delete("/sections/{section_id}")
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(Section, section_id)
    assert_school_entity(row, school_id, "Section")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/teachers", response_model=list[TeacherOut])
def list_teachers(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    rows = (
        db.query(Teacher)
        .options(joinedload(Teacher.subjects))
        .filter(Teacher.school_id == school_id)
        .all()
    )
    return [_teacher_out(t) for t in rows]


@router.post("/teachers", response_model=TeacherOut)
def create_teacher(
    body: TeacherIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    data = body.model_dump(exclude={"subject_ids", "username", "password"})
    row = Teacher(school_id=school_id, **data)
    db.add(row)
    db.flush()
    for sid in body.subject_ids:
        db.add(TeacherSubject(school_id=school_id, teacher_id=row.id, subject_id=sid))
    school = db.get(School, school_id)
    maybe_create_teacher_login(
        db,
        school=school,
        teacher=row,
        username=body.username,
        password=body.password,
        email=body.email,
    )
    write_audit(db, user, "create_teacher", "teacher", row.id, school_id=school_id)
    db.commit()
    db.refresh(row)
    return _teacher_out(row)


@router.put("/teachers/{teacher_id}", response_model=TeacherOut)
def update_teacher(
    teacher_id: int,
    body: TeacherIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(Teacher, teacher_id)
    assert_school_entity(row, school_id, "Teacher")
    for k, v in body.model_dump(exclude={"subject_ids", "username", "password"}).items():
        setattr(row, k, v)
    db.query(TeacherSubject).filter(TeacherSubject.teacher_id == teacher_id).delete()
    for sid in body.subject_ids:
        db.add(TeacherSubject(school_id=school_id, teacher_id=row.id, subject_id=sid))
    db.commit()
    row = db.get(Teacher, teacher_id, options=[joinedload(Teacher.subjects)])
    return _teacher_out(row)


@router.delete("/teachers/{teacher_id}")
def delete_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(Teacher, teacher_id)
    assert_school_entity(row, school_id, "Teacher")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/teachers/{teacher_id}/availability", response_model=list[TeacherAvailabilityOut])
def get_availability(
    teacher_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
):
    row = db.get(Teacher, teacher_id)
    assert_school_entity(row, school_id, "Teacher")
    return db.query(TeacherAvailability).filter(TeacherAvailability.teacher_id == teacher_id).all()


@router.put("/teachers/{teacher_id}/availability", response_model=list[TeacherAvailabilityOut])
def set_availability(
    teacher_id: int,
    body: list[AvailabilityIn],
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(Teacher, teacher_id)
    assert_school_entity(row, school_id, "Teacher")
    db.query(TeacherAvailability).filter(TeacherAvailability.teacher_id == teacher_id).delete()
    out = []
    for item in body:
        rec = TeacherAvailability(school_id=school_id, teacher_id=teacher_id, **item.model_dump())
        db.add(rec)
        out.append(rec)
    write_audit(db, user, "set_availability", "teacher", teacher_id, school_id=school_id)
    db.commit()
    return out


@router.get("/assignments", response_model=list[AssignmentOut])
def list_assignments(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    rows = (
        db.query(TeacherClassAssignment)
        .options(
            joinedload(TeacherClassAssignment.teacher),
            joinedload(TeacherClassAssignment.subject),
            joinedload(TeacherClassAssignment.section).joinedload(Section.school_class),
        )
        .filter(TeacherClassAssignment.school_id == school_id)
        .all()
    )
    return [
        AssignmentOut(
            id=a.id,
            school_id=a.school_id,
            teacher_id=a.teacher_id,
            section_id=a.section_id,
            subject_id=a.subject_id,
            weekly_periods=a.weekly_periods,
            teacher_name=a.teacher.name,
            section_label=section_label(a.section),
            subject_name=a.subject.name,
        )
        for a in rows
    ]


@router.post("/assignments", response_model=AssignmentOut)
def create_assignment(
    body: AssignmentIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    for attr, model in (
        ("teacher_id", Teacher),
        ("section_id", Section),
    ):
        ent = db.get(model, getattr(body, attr))
        assert_school_entity(ent, school_id, attr)
    row = TeacherClassAssignment(school_id=school_id, **body.model_dump())
    db.add(row)
    db.commit()
    row = db.get(
        TeacherClassAssignment,
        row.id,
        options=[
            joinedload(TeacherClassAssignment.teacher),
            joinedload(TeacherClassAssignment.subject),
            joinedload(TeacherClassAssignment.section).joinedload(Section.school_class),
        ],
    )
    return AssignmentOut(
        id=row.id,
        school_id=row.school_id,
        teacher_id=row.teacher_id,
        section_id=row.section_id,
        subject_id=row.subject_id,
        weekly_periods=row.weekly_periods,
        teacher_name=row.teacher.name,
        section_label=section_label(row.section),
        subject_name=row.subject.name,
    )


@router.delete("/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(TeacherClassAssignment, assignment_id)
    assert_school_entity(row, school_id, "Assignment")
    db.delete(row)
    db.commit()
    return {"ok": True}
