from __future__ import annotations

import enum
from datetime import date, datetime, time

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def str_enum(enum_cls):
    return Enum(enum_cls, native_enum=False, length=40, validate_strings=True)


class RoleName(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class SubjectType(str, enum.Enum):
    ACADEMIC = "academic"
    PRACTICAL = "practical"
    SPORTS = "sports"
    ACTIVITY = "activity"
    LAB = "lab"
    OTHER = "other"


class RoomType(str, enum.Enum):
    CLASSROOM = "classroom"
    COMPUTER_LAB = "computer_lab"
    SCIENCE_LAB = "science_lab"
    LIBRARY = "library"
    PLAYGROUND = "playground"
    AUDITORIUM = "auditorium"
    OTHER = "other"


class ConstraintKind(str, enum.Enum):
    HARD = "hard"
    SOFT = "soft"


class TimetableStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    PUBLISHED = "published"
    CONFLICTED = "conflicted"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[RoleName] = mapped_column(str_enum(RoleName), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")

    users: Mapped[list[User]] = relationship(back_populates="role")


class School(Base, TimestampMixin):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(400), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    setup_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    users: Mapped[list[User]] = relationship(back_populates="school")
    academic_years: Mapped[list[AcademicYear]] = relationship(back_populates="school")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), nullable=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    username: Mapped[str | None] = mapped_column(String(80), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    school: Mapped[School | None] = relationship(back_populates="users")
    role: Mapped[Role] = relationship(back_populates="users")
    teacher: Mapped[Teacher | None] = relationship(back_populates="user", uselist=False)


class AcademicYear(Base, TimestampMixin):
    __tablename__ = "academic_years"
    __table_args__ = (UniqueConstraint("school_id", "name", name="uq_year_school_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    school: Mapped[School] = relationship(back_populates="academic_years")


class Day(Base):
    __tablename__ = "days"
    __table_args__ = (UniqueConstraint("school_id", "weekday", name="uq_day_school_weekday"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon
    is_working: Mapped[bool] = mapped_column(Boolean, default=True)


class Period(Base):
    __tablename__ = "periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    academic_year_id: Mapped[int | None] = mapped_column(ForeignKey("academic_years.id"))
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    period_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)
    is_free_slot: Mapped[bool] = mapped_column(Boolean, default=False)


class SchoolClass(Base, TimestampMixin):
    __tablename__ = "classes"
    __table_args__ = (UniqueConstraint("school_id", "name", "academic_year_id", name="uq_class_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    academic_year_id: Mapped[int | None] = mapped_column(ForeignKey("academic_years.id"))
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, default=0)

    sections: Mapped[list[Section]] = relationship(back_populates="school_class", cascade="all, delete-orphan")


class Section(Base, TimestampMixin):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("class_id", "name", name="uq_section_class_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(40), default="")
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)

    school_class: Mapped[SchoolClass] = relationship(back_populates="sections")
    home_room: Mapped[Room | None] = relationship(foreign_keys=[room_id])

    @property
    def label(self) -> str:
        return self.display_name or f"{self.school_class.name}{self.name}" if self.school_class else self.name


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    short_name: Mapped[str] = mapped_column(String(20), default="")
    code: Mapped[str] = mapped_column(String(20), default="")
    subject_type: Mapped[SubjectType] = mapped_column(str_enum(SubjectType), default=SubjectType.ACADEMIC)
    weekly_required_periods: Mapped[int] = mapped_column(Integer, default=1)
    preferred_periods: Mapped[list] = mapped_column(JSON, default=list)
    can_be_consecutive: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_room: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_special_teacher: Mapped[bool] = mapped_column(Boolean, default=False)
    required_room_type: Mapped[RoomType | None] = mapped_column(str_enum(RoomType), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    is_difficult: Mapped[bool] = mapped_column(Boolean, default=False)


class Teacher(Base, TimestampMixin):
    __tablename__ = "teachers"
    __table_args__ = (UniqueConstraint("school_id", "employee_id", name="uq_teacher_emp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    max_periods_day: Mapped[int] = mapped_column(Integer, default=6)
    max_periods_week: Mapped[int] = mapped_column(Integer, default=30)
    min_periods_day: Mapped[int] = mapped_column(Integer, default=0)
    preferred_periods: Mapped[list] = mapped_column(JSON, default=list)

    user: Mapped[User | None] = relationship(back_populates="teacher")
    subjects: Mapped[list[TeacherSubject]] = relationship(cascade="all, delete-orphan")
    assignments: Mapped[list[TeacherClassAssignment]] = relationship(cascade="all, delete-orphan")
    availability: Mapped[list[TeacherAvailability]] = relationship(cascade="all, delete-orphan")


class TeacherSubject(Base):
    __tablename__ = "teacher_subjects"
    __table_args__ = (UniqueConstraint("teacher_id", "subject_id", name="uq_teacher_subject"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)


class TeacherClassAssignment(Base):
    __tablename__ = "teacher_class_assignments"
    __table_args__ = (
        UniqueConstraint("teacher_id", "section_id", "subject_id", name="uq_teacher_section_subject"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    weekly_periods: Mapped[int | None] = mapped_column(Integer, nullable=True)

    teacher: Mapped[Teacher] = relationship(back_populates="assignments")
    section: Mapped[Section] = relationship()
    subject: Mapped[Subject] = relationship()


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=40)
    room_type: Mapped[RoomType] = mapped_column(str_enum(RoomType), default=RoomType.CLASSROOM)
    allowed_subject_ids: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    availability: Mapped[list[RoomAvailability]] = relationship(cascade="all, delete-orphan")


class RoomAvailability(Base):
    __tablename__ = "room_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id"), nullable=False)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)


class TeacherAvailability(Base):
    __tablename__ = "teacher_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id"), nullable=False)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False)
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(String(255), default="")


class SubjectRequirement(Base):
    __tablename__ = "subject_requirements"
    __table_args__ = (UniqueConstraint("section_id", "subject_id", name="uq_section_subject_req"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    weekly_periods: Mapped[int] = mapped_column(Integer, nullable=False)
    preferred_periods: Mapped[list] = mapped_column(JSON, default=list)


class SchedulingRule(Base, TimestampMixin):
    __tablename__ = "scheduling_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[ConstraintKind] = mapped_column(str_enum(ConstraintKind), default=ConstraintKind.SOFT)
    constraint_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    weight: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(40), default="manual")  # manual | gemini
    natural_language: Mapped[str] = mapped_column(Text, default="")


class TimetableVersion(Base, TimestampMixin):
    __tablename__ = "timetable_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    academic_year_id: Mapped[int | None] = mapped_column(ForeignKey("academic_years.id"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[TimetableStatus] = mapped_column(str_enum(TimetableStatus), default=TimetableStatus.DRAFT)
    score: Mapped[float] = mapped_column(Float, default=0)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    constraint_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    unsatisfied_preferences: Mapped[list] = mapped_column(JSON, default=list)
    generation_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_version_id: Mapped[int | None] = mapped_column(ForeignKey("timetable_versions.id"), nullable=True)
    solver_notes: Mapped[str] = mapped_column(Text, default="")

    entries: Mapped[list[TimetableEntry]] = relationship(cascade="all, delete-orphan")


class TimetableEntry(Base, TimestampMixin):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        UniqueConstraint("version_id", "section_id", "day_id", "period_id", name="uq_entry_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("timetable_versions.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), nullable=False)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id"), nullable=False)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id"), nullable=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(String(255), default="")

    version: Mapped[TimetableVersion] = relationship(back_populates="entries")
    section: Mapped[Section] = relationship()
    day: Mapped[Day] = relationship()
    period: Mapped[Period] = relationship()
    subject: Mapped[Subject | None] = relationship()
    teacher: Mapped[Teacher | None] = relationship()
    room: Mapped[Room | None] = relationship()


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    channel: Mapped[NotificationChannel] = mapped_column(
        str_enum(NotificationChannel), default=NotificationChannel.IN_APP
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), default="")
    entity_id: Mapped[str] = mapped_column(String(40), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AiConversation(Base, TimestampMixin):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="Assistant")
    messages: Mapped[list] = mapped_column(JSON, default=list)


class AiRequest(Base):
    __tablename__ = "ai_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("ai_conversations.id"))
    endpoint: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="")
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
