from datetime import date, time

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import hash_password
from app.models.entities import (
    AcademicYear,
    AiConversation,
    AiRequest,
    AuditLog,
    ConstraintKind,
    Day,
    Notification,
    Period,
    Role,
    RoleName,
    Room,
    RoomAvailability,
    RoomType,
    SchedulingRule,
    School,
    SchoolClass,
    Section,
    Subject,
    SubjectRequirement,
    SubjectType,
    Teacher,
    TeacherAvailability,
    TeacherClassAssignment,
    TeacherSubject,
    TimetableEntry,
    TimetableVersion,
    User,
)

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

DEFAULT_PERIODS = [
    ("Period 1", 1, time(8, 0), time(8, 40), False),
    ("Period 2", 2, time(8, 40), time(9, 20), False),
    ("Period 3", 3, time(9, 20), time(10, 0), False),
    ("Period 4", 4, time(10, 0), time(10, 40), False),
    ("Break", 5, time(10, 40), time(11, 0), True),
    ("Period 5", 6, time(11, 0), time(11, 40), False),
    ("Period 6", 7, time(11, 40), time(12, 20), False),
    ("Period 7", 8, time(12, 20), time(13, 0), False),
]


def bootstrap(db: Session) -> None:
    settings = get_settings()
    for role in RoleName:
        if db.query(Role).filter(Role.name == role).first() is None:
            db.add(Role(name=role, description=role.value.replace("_", " ").title()))
    db.flush()
    _ensure_super_admin(db, settings)
    db.commit()


def _ensure_super_admin(db: Session, settings) -> None:
    super_role = db.query(Role).filter(Role.name == RoleName.SUPER_ADMIN).first()
    username = (settings.bootstrap_super_username or "superAdmin").strip()
    email = (settings.bootstrap_super_email or "superadmin@sanjivani.app").strip().lower()
    user = (
        db.query(User)
        .filter(
            or_(
                User.role_id == super_role.id,
                func.lower(User.username) == username.lower(),
                User.email == email,
                User.email == "admin@sanjivani.app",
            )
        )
        .first()
    )
    if user is None:
        db.add(
            User(
                school_id=None,
                role_id=super_role.id,
                username=username,
                email=email,
                hashed_password=hash_password(settings.bootstrap_super_password),
                full_name="Super Admin",
            )
        )
        return
    user.role_id = super_role.id
    user.school_id = None
    user.username = username
    user.email = email
    user.hashed_password = hash_password(settings.bootstrap_super_password)
    user.is_active = True
    if not user.full_name:
        user.full_name = "Super Admin"


def _wipe_school(db: Session, school_id: int, keep_emails: set[str]) -> None:
    teachers = db.query(Teacher).filter(Teacher.school_id == school_id).all()
    for t in teachers:
        t.user_id = None
    db.flush()
    for model in (
        TimetableEntry,
        TimetableVersion,
        TeacherAvailability,
        TeacherClassAssignment,
        TeacherSubject,
        RoomAvailability,
        SubjectRequirement,
        SchedulingRule,
        Notification,
        AiRequest,
        AiConversation,
        AuditLog,
        Teacher,
        Section,
        SchoolClass,
        Subject,
        Room,
        Period,
        Day,
        AcademicYear,
    ):
        db.query(model).filter(model.school_id == school_id).delete(synchronize_session=False)
    db.query(User).filter(User.school_id == school_id, User.email.notin_(keep_emails)).delete(
        synchronize_session=False
    )
    db.flush()


def seed_demo_school(db: Session, replace: bool = False) -> School:
    """3 classes, 7 subjects, 11 teachers — weekly load always under 30 periods."""
    existing = db.query(School).filter(School.code == "demo").first()
    if existing and not replace:
        return existing
    if existing:
        _wipe_school(db, existing.id, keep_emails={"admin@demo.school"})
        school = existing
        school.name = "Sanjivani Demo School"
        school.setup_completed = True
    else:
        school = School(
            name="Sanjivani Demo School",
            code="demo",
            setup_completed=True,
            timezone="Asia/Kolkata",
        )
        db.add(school)
        db.flush()

    admin_role = db.query(Role).filter(Role.name == RoleName.SCHOOL_ADMIN).first()
    teacher_role = db.query(Role).filter(Role.name == RoleName.TEACHER).first()
    student_role = db.query(Role).filter(Role.name == RoleName.STUDENT).first()
    admin = db.query(User).filter(User.email == "admin@demo.school").first()
    if admin is None:
        db.add(
            User(
                school_id=school.id,
                role_id=admin_role.id,
                email="admin@demo.school",
                hashed_password=hash_password("DemoAdmin123!"),
                full_name="School Administrator",
            )
        )
    else:
        admin.school_id = school.id
        admin.hashed_password = hash_password("DemoAdmin123!")

    year = AcademicYear(
        school_id=school.id,
        name="2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    db.add(year)
    days = []
    for i, name in enumerate(DAY_NAMES):
        d = Day(school_id=school.id, name=name, weekday=i, is_working=True)
        db.add(d)
        days.append(d)
    periods = []
    for name, idx, start, end, brk in DEFAULT_PERIODS:
        p = Period(
            school_id=school.id,
            academic_year_id=year.id,
            name=name,
            period_index=idx,
            start_time=start,
            end_time=end,
            is_break=brk,
        )
        db.add(p)
        periods.append(p)
    db.flush()

    sections: list[Section] = []
    for cname, grade, secs in (("6", 6, ["A", "B"]), ("7", 7, ["A", "B"]), ("8", 8, ["A", "B"])):
        cls = SchoolClass(school_id=school.id, academic_year_id=year.id, name=cname, grade_level=grade)
        db.add(cls)
        db.flush()
        for s in secs:
            sec = Section(school_id=school.id, class_id=cls.id, name=s, display_name=f"{cname}{s}")
            db.add(sec)
            sections.append(sec)
    db.flush()

    subject_specs = [
        ("Mathematics", "MATH", "MTH", SubjectType.ACADEMIC, 6, True, 9, False, None),
        ("Science", "SCI", "SCI", SubjectType.ACADEMIC, 5, True, 8, False, None),
        ("English", "ENG", "ENG", SubjectType.ACADEMIC, 6, True, 7, False, None),
        ("Hindi", "HIN", "HIN", SubjectType.ACADEMIC, 4, False, 5, False, None),
        ("Social Studies", "SST", "SST", SubjectType.ACADEMIC, 4, False, 5, False, None),
        ("Computer", "COMP", "CMP", SubjectType.LAB, 2, False, 5, True, RoomType.COMPUTER_LAB),
        ("Physical Education", "PE", "PED", SubjectType.SPORTS, 2, False, 3, True, RoomType.PLAYGROUND),
    ]
    subjects: dict[str, Subject] = {}
    for name, short, code, stype, weekly, difficult, prio, req_room, rtype in subject_specs:
        s = Subject(
            school_id=school.id,
            name=name,
            short_name=short,
            code=code,
            subject_type=stype,
            weekly_required_periods=weekly,
            preferred_periods=[1, 2, 3] if difficult else [],
            can_be_consecutive=name != "Mathematics",
            requires_room=req_room,
            required_room_type=rtype,
            priority=prio,
            is_difficult=difficult,
        )
        db.add(s)
        subjects[name] = s
    db.flush()

    special_rooms = [
        Room(
            school_id=school.id,
            name="Computer Lab",
            capacity=40,
            room_type=RoomType.COMPUTER_LAB,
            allowed_subject_ids=[subjects["Computer"].id],
        ),
        Room(
            school_id=school.id,
            name="Science Lab",
            capacity=40,
            room_type=RoomType.SCIENCE_LAB,
            allowed_subject_ids=[subjects["Science"].id],
        ),
        Room(
            school_id=school.id,
            name="Playground",
            capacity=80,
            room_type=RoomType.PLAYGROUND,
            allowed_subject_ids=[subjects["Physical Education"].id],
        ),
        Room(school_id=school.id, name="Library", capacity=50, room_type=RoomType.LIBRARY),
        Room(school_id=school.id, name="Auditorium", capacity=200, room_type=RoomType.AUDITORIUM),
    ]
    db.add_all(special_rooms)
    db.flush()
    for sec in sections:
        room = Room(
            school_id=school.id,
            name=f"Room {sec.display_name}",
            capacity=40,
            room_type=RoomType.CLASSROOM,
        )
        db.add(room)
        db.flush()
        sec.room_id = room.id

    teacher_specs = [
        ("Mr Sharma", "T001", "Mathematics"),
        ("Mrs Iyer", "T002", "Mathematics"),
        ("Mrs Gupta", "T003", "English"),
        ("Mr Bose", "T004", "English"),
        ("Mr Singh", "T005", "Science"),
        ("Ms Das", "T006", "Science"),
        ("Ms Patel", "T007", "Hindi"),
        ("Mrs Nair", "T008", "Hindi"),
        ("Mr Verma", "T009", "Social Studies"),
        ("Mr Khan", "T010", "Computer"),
        ("Coach Rao", "T011", "Physical Education"),
    ]
    by_subject: dict[str, list[Teacher]] = {}
    sharma: Teacher | None = None
    for name, emp, subj in teacher_specs:
        t = Teacher(
            school_id=school.id,
            name=name,
            employee_id=emp,
            email=f"{emp.lower()}@demo.school",
            max_periods_day=6,
            max_periods_week=30,
        )
        db.add(t)
        db.flush()
        db.add(TeacherSubject(school_id=school.id, teacher_id=t.id, subject_id=subjects[subj].id))
        user = User(
            school_id=school.id,
            role_id=teacher_role.id,
            email=f"{emp.lower()}@demo.school",
            hashed_password=hash_password("Teacher123!"),
            full_name=name,
        )
        db.add(user)
        db.flush()
        t.user_id = user.id
        by_subject.setdefault(subj, []).append(t)
        if emp == "T001":
            sharma = t

    wed = next(d for d in days if d.weekday == 2)
    p3 = next(p for p in periods if p.period_index == 3)
    if sharma:
        db.add(
            TeacherAvailability(
                school_id=school.id,
                teacher_id=sharma.id,
                day_id=wed.id,
                period_id=p3.id,
                is_available=False,
                reason="Unavailable Wednesday Period 3",
            )
        )

    def assign(teacher: Teacher, subject_name: str, section: Section) -> None:
        db.add(
            TeacherClassAssignment(
                school_id=school.id,
                teacher_id=teacher.id,
                section_id=section.id,
                subject_id=subjects[subject_name].id,
                weekly_periods=subjects[subject_name].weekly_required_periods,
            )
        )

    def split(subject_name: str) -> None:
        pool = by_subject[subject_name]
        for i, sec in enumerate(sections):
            assign(pool[i % len(pool)], subject_name, sec)

    for subject_name in (
        "Mathematics",
        "English",
        "Science",
        "Hindi",
        "Social Studies",
        "Computer",
        "Physical Education",
    ):
        split(subject_name)

    db.add(
        User(
            school_id=school.id,
            role_id=student_role.id,
            email="parent@demo.school",
            hashed_password=hash_password("Parent123!"),
            full_name="Parent Viewer",
        )
    )

    for name, ctype, weight in (
        ("Morning difficult subjects", "morning_difficult", 8),
        ("Avoid consecutive same subject", "avoid_consecutive", 10),
        ("Teacher gap penalty", "teacher_gap", 5),
        ("Preferred morning periods", "preferred_periods", 8),
        ("Spread subjects across the week", "distribute_week", 7),
        ("Avoid same period every day", "avoid_same_period_daily", 6),
        ("Limit difficult cluster", "difficult_day_cluster", 7),
        ("Avoid triple consecutive", "triple_consecutive", 12),
    ):
        db.add(
            SchedulingRule(
                school_id=school.id,
                name=name,
                kind=ConstraintKind.SOFT,
                constraint_type=ctype,
                payload={},
                weight=weight,
                source="manual",
            )
        )
    db.commit()
    db.refresh(school)
    return school
