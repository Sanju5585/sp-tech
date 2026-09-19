from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.accounts import create_login_user
from app.core.audit import write_audit
from app.core.rbac import assert_school_entity, get_tenant_school_id, require_roles
from app.database import get_db
from app.models.entities import AcademicYear, Day, Period, RoleName, School, User
from app.schemas import (
    AcademicYearOut,
    DayOut,
    PeriodIn,
    PeriodOut,
    SchoolCreate,
    SchoolOut,
    SchoolUpdate,
    SchoolWithAdmins,
    SetupStep1,
    SetupStep2,
    UserOut,
)

router = APIRouter(tags=["schools"])
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
Admin = require_roles(RoleName.SUPER_ADMIN, RoleName.SCHOOL_ADMIN)
SuperAdmin = require_roles(RoleName.SUPER_ADMIN)


def _school_with_admins(db: Session, school: School) -> SchoolWithAdmins:
    admins = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.school_id == school.id)
        .all()
    )
    admin_users = [UserOut.from_user(u) for u in admins if u.role.name == RoleName.SCHOOL_ADMIN]
    return SchoolWithAdmins(
        id=school.id,
        name=school.name,
        code=school.code,
        address=school.address,
        phone=school.phone,
        timezone=school.timezone,
        setup_completed=school.setup_completed,
        settings=school.settings or {},
        admins=admin_users,
    )


@router.get("/schools/me", response_model=SchoolOut)
def get_my_school(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    school = db.get(School, school_id)
    assert_school_entity(school, school_id, "School")
    return school


@router.put("/schools/me", response_model=SchoolOut)
def update_school(
    body: SchoolUpdate,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    school = db.get(School, school_id)
    assert_school_entity(school, school_id, "School")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(school, field, value)
    write_audit(db, user, "update_school", "school", school.id, school_id=school_id)
    db.commit()
    db.refresh(school)
    return school


@router.get("/schools", response_model=list[SchoolWithAdmins])
def list_schools(db: Session = Depends(get_db), user: User = Depends(SuperAdmin)):
    return [_school_with_admins(db, s) for s in db.query(School).order_by(School.name).all()]


@router.post("/schools", response_model=SchoolWithAdmins)
def create_school(
    body: SchoolCreate,
    db: Session = Depends(get_db),
    user: User = Depends(SuperAdmin),
):
    code = body.code.strip().lower()
    if db.query(School).filter(School.code == code).first():
        raise HTTPException(409, "School code already in use")
    school = School(
        name=body.name.strip(),
        code=code,
        address=body.address,
        phone=body.phone,
        timezone="Asia/Kolkata",
    )
    db.add(school)
    db.flush()
    create_login_user(
        db,
        school=school,
        role=RoleName.SCHOOL_ADMIN,
        full_name=body.admin_full_name,
        username=body.admin_username,
        password=body.admin_password,
        email=body.admin_email,
        phone=body.phone,
    )
    write_audit(db, user, "create_school", "school", school.id, {"school": school.name}, school.id)
    db.commit()
    school = db.get(School, school.id)
    return _school_with_admins(db, school)


@router.post("/setup/school", response_model=AcademicYearOut)
def setup_step1(
    body: SetupStep1,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    school = db.get(School, school_id)
    school.name = body.school_name
    db.query(AcademicYear).filter(AcademicYear.school_id == school_id).update({"is_current": False})
    year = AcademicYear(
        school_id=school_id,
        name=body.academic_year,
        start_date=body.start_date,
        end_date=body.end_date,
        is_current=True,
    )
    db.add(year)
    db.query(Day).filter(Day.school_id == school_id).delete()
    working = set(body.working_days)
    for i, name in enumerate(DAY_NAMES[:6]):
        db.add(Day(school_id=school_id, name=name, weekday=i, is_working=i in working))
    write_audit(db, user, "setup_step1", "academic_year", details=body.model_dump(), school_id=school_id)
    db.commit()
    db.refresh(year)
    return year


@router.post("/setup/periods", response_model=list[PeriodOut])
def setup_step2(
    body: SetupStep2,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    db.query(Period).filter(Period.school_id == school_id).delete()
    year = (
        db.query(AcademicYear)
        .filter(AcademicYear.school_id == school_id, AcademicYear.is_current.is_(True))
        .first()
    )
    created = []
    for p in body.periods:
        row = Period(
            school_id=school_id,
            academic_year_id=year.id if year else None,
            name=p.name,
            period_index=p.period_index,
            start_time=p.start_time,
            end_time=p.end_time,
            is_break=p.is_break,
            is_free_slot=p.is_free_slot,
        )
        db.add(row)
        created.append(row)
    school = db.get(School, school_id)
    school.setup_completed = True
    write_audit(db, user, "setup_step2", "period", school_id=school_id)
    db.commit()
    return created


@router.get("/days", response_model=list[DayOut])
def list_days(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    return db.query(Day).filter(Day.school_id == school_id).order_by(Day.weekday).all()


@router.get("/periods", response_model=list[PeriodOut])
def list_periods(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    return db.query(Period).filter(Period.school_id == school_id).order_by(Period.period_index).all()


@router.post("/periods", response_model=PeriodOut)
def create_period(
    body: PeriodIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = Period(school_id=school_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/periods/{period_id}", response_model=PeriodOut)
def update_period(
    period_id: int,
    body: PeriodIn,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(Period, period_id)
    assert_school_entity(row, school_id, "Period")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/periods/{period_id}")
def delete_period(
    period_id: int,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
    user: User = Depends(Admin),
):
    row = db.get(Period, period_id)
    assert_school_entity(row, school_id, "Period")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/academic-years", response_model=list[AcademicYearOut])
def list_years(db: Session = Depends(get_db), school_id: int = Depends(get_tenant_school_id)):
    return db.query(AcademicYear).filter(AcademicYear.school_id == school_id).all()
