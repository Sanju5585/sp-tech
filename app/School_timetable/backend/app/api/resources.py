from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import assert_school_entity, get_tenant_school_id, require_roles
from app.database import get_db
from app.models.entities import RoleName, Room, SchedulingRule, Subject, SubjectRequirement, User
from app.schemas import RoomIn, RoomOut, RuleIn, RuleOut, SubjectIn, SubjectOut, SubjectRequirementIn

router = APIRouter(tags=["resources"])
Admin = require_roles(RoleName.SUPER_ADMIN, RoleName.SCHOOL_ADMIN)


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    return db.query(Subject).filter(Subject.school_id == school_id).order_by(Subject.name).all()


@router.post("/subjects", response_model=SubjectOut)
def create_subject(
    body: SubjectIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = Subject(school_id=school_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: int,
    body: SubjectIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(Subject, subject_id)
    assert_school_entity(row, school_id, "Subject")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/subjects/{subject_id}")
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(Subject, subject_id)
    assert_school_entity(row, school_id, "Subject")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/rooms", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    return db.query(Room).filter(Room.school_id == school_id).order_by(Room.name).all()


@router.post("/rooms", response_model=RoomOut)
def create_room(
    body: RoomIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = Room(school_id=school_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/rooms/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int,
    body: RoomIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(Room, room_id)
    assert_school_entity(row, school_id, "Room")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/rooms/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(Room, room_id)
    assert_school_entity(row, school_id, "Room")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/rules", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    return db.query(SchedulingRule).filter(SchedulingRule.school_id == school_id).all()


@router.post("/rules", response_model=RuleOut)
def create_rule(
    body: RuleIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = SchedulingRule(school_id=school_id, source="manual", **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/rules/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: int,
    body: RuleIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(SchedulingRule, rule_id)
    assert_school_entity(row, school_id, "Rule")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(SchedulingRule, rule_id)
    assert_school_entity(row, school_id, "Rule")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/subject-requirements")
def upsert_requirement(
    body: SubjectRequirementIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    existing = (
        db.query(SubjectRequirement)
        .filter(
            SubjectRequirement.school_id == school_id,
            SubjectRequirement.section_id == body.section_id,
            SubjectRequirement.subject_id == body.subject_id,
        )
        .first()
    )
    if existing:
        existing.weekly_periods = body.weekly_periods
        existing.preferred_periods = body.preferred_periods
        row = existing
    else:
        row = SubjectRequirement(school_id=school_id, **body.model_dump())
        db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "weekly_periods": row.weekly_periods}
