from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import (
    ConstraintKind,
    NotificationChannel,
    RoleName,
    RoomType,
    SubjectType,
    TimetableStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Auth ────────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    school_name: str = Field(min_length=2, max_length=200)
    school_code: str = Field(min_length=2, max_length=40)
    full_name: str = Field(min_length=2, max_length=200)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    phone: str = ""
    username: str = Field(default="", max_length=80)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, description="Username or email")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: RoleName
    school_id: int | None = None
    user_id: int
    full_name: str
    teacher_id: int | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class PortalSsoRequest(BaseModel):
    token: str


class UserOut(ORMModel):
    id: int
    username: str = ""
    email: str
    full_name: str
    phone: str
    is_active: bool
    school_id: int | None
    role: RoleName

    @classmethod
    def from_user(cls, user) -> "UserOut":
        return cls(
            id=user.id,
            username=user.username or "",
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            is_active=user.is_active,
            school_id=user.school_id,
            role=user.role.name,
        )


class SchoolCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40)
    address: str = ""
    phone: str = ""
    admin_full_name: str = Field(min_length=2, max_length=200)
    admin_username: str = Field(min_length=3, max_length=80)
    admin_email: str = ""
    admin_password: str = Field(min_length=8, max_length=128)


class StaffUserIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    email: str = ""
    phone: str = ""
    role: Literal["school_admin", "teacher", "student", "parent"] = "teacher"
    school_id: int | None = None
    employee_id: str = ""


class UserStatusIn(BaseModel):
    is_active: bool


# ── School / setup ──────────────────────────────────────────────────────────


class SchoolOut(ORMModel):
    id: int
    name: str
    code: str
    address: str
    phone: str
    timezone: str
    setup_completed: bool
    settings: dict = {}


class SchoolWithAdmins(SchoolOut):
    admins: list[UserOut] = []


class SchoolUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    timezone: str | None = None
    settings: dict | None = None


class SetupStep1(BaseModel):
    school_name: str
    academic_year: str
    start_date: date
    end_date: date
    working_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5])


class PeriodIn(BaseModel):
    name: str
    period_index: int
    start_time: time
    end_time: time
    is_break: bool = False
    is_free_slot: bool = False


class SetupStep2(BaseModel):
    periods: list[PeriodIn]


# ── Domain entities ─────────────────────────────────────────────────────────


class ClassIn(BaseModel):
    name: str
    grade_level: int = 0
    sections: list[str] = Field(default_factory=list)


class ClassUpdate(BaseModel):
    name: str | None = None
    grade_level: int | None = None


class SectionIn(BaseModel):
    class_id: int
    name: str
    display_name: str = ""
    room_id: int | None = None


class SectionOut(ORMModel):
    id: int
    school_id: int
    class_id: int
    name: str
    display_name: str
    room_id: int | None
    label: str = ""


class ClassOut(ORMModel):
    id: int
    school_id: int
    name: str
    grade_level: int
    sections: list[SectionOut] = []


class SubjectIn(BaseModel):
    name: str
    short_name: str = ""
    code: str = ""
    subject_type: SubjectType = SubjectType.ACADEMIC
    weekly_required_periods: int = 1
    preferred_periods: list[int] = Field(default_factory=list)
    can_be_consecutive: bool = True
    requires_room: bool = False
    requires_special_teacher: bool = False
    required_room_type: RoomType | None = None
    priority: int = 5
    is_difficult: bool = False


class SubjectOut(SubjectIn, ORMModel):
    id: int
    school_id: int


class TeacherIn(BaseModel):
    name: str
    employee_id: str
    email: str = ""
    phone: str = ""
    max_periods_day: int = 6
    max_periods_week: int = 30
    min_periods_day: int = 0
    preferred_periods: list[int] = Field(default_factory=list)
    subject_ids: list[int] = Field(default_factory=list)
    username: str = ""
    password: str = ""


class TeacherOut(ORMModel):
    id: int
    school_id: int
    name: str
    employee_id: str
    email: str
    phone: str
    max_periods_day: int
    max_periods_week: int
    min_periods_day: int
    preferred_periods: list = []
    subject_ids: list[int] = []
    user_id: int | None = None


class AssignmentIn(BaseModel):
    teacher_id: int
    section_id: int
    subject_id: int
    weekly_periods: int | None = None


class AssignmentOut(ORMModel):
    id: int
    school_id: int
    teacher_id: int
    section_id: int
    subject_id: int
    weekly_periods: int | None = None
    teacher_name: str = ""
    section_label: str = ""
    subject_name: str = ""


class RoomIn(BaseModel):
    name: str
    capacity: int = 40
    room_type: RoomType = RoomType.CLASSROOM
    allowed_subject_ids: list[int] = Field(default_factory=list)


class RoomOut(RoomIn, ORMModel):
    id: int
    school_id: int
    is_active: bool = True


class AvailabilityIn(BaseModel):
    day_id: int
    period_id: int
    is_available: bool = False
    is_preferred: bool = False
    reason: str = ""


class TeacherAvailabilityOut(AvailabilityIn, ORMModel):
    id: int
    teacher_id: int


class PeriodOut(ORMModel):
    id: int
    school_id: int
    name: str
    period_index: int
    start_time: time
    end_time: time
    is_break: bool
    is_free_slot: bool


class DayOut(ORMModel):
    id: int
    school_id: int
    name: str
    weekday: int
    is_working: bool


class AcademicYearOut(ORMModel):
    id: int
    school_id: int
    name: str
    start_date: date
    end_date: date
    is_current: bool


class RuleIn(BaseModel):
    name: str
    kind: ConstraintKind = ConstraintKind.SOFT
    constraint_type: str
    payload: dict = Field(default_factory=dict)
    weight: int = 5
    is_active: bool = True
    natural_language: str = ""


class RuleOut(RuleIn, ORMModel):
    id: int
    school_id: int
    source: str = "manual"


class SubjectRequirementIn(BaseModel):
    section_id: int
    subject_id: int
    weekly_periods: int
    preferred_periods: list[int] = Field(default_factory=list)


# ── Timetable ───────────────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    alternatives: int = Field(default=1, ge=1, le=8)
    time_limit_seconds: int | None = None
    lock_existing: bool = False
    version_name: str | None = None
    morning_hard_subjects: Literal["prefer", "require", "anytime"] = "prefer"


class EntryOut(ORMModel):
    id: int
    version_id: int
    section_id: int
    day_id: int
    period_id: int
    subject_id: int | None
    teacher_id: int | None
    room_id: int | None
    is_free: bool
    is_locked: bool
    notes: str = ""
    subject_name: str = ""
    subject_short: str = ""
    teacher_name: str = ""
    room_name: str = ""
    section_label: str = ""
    day_name: str = ""
    period_name: str = ""
    period_index: int = 0


class VersionOut(ORMModel):
    id: int
    school_id: int
    name: str
    status: TimetableStatus
    score: float
    score_breakdown: dict = {}
    constraint_stats: dict = {}
    warnings: list = []
    unsatisfied_preferences: list = []
    generation_time_ms: int = 0
    is_selected: bool = False
    created_at: datetime | None = None


class GenerateResponse(BaseModel):
    versions: list[VersionOut]
    selected_id: int | None = None


class ConflictItem(BaseModel):
    type: Literal["hard", "soft"]
    code: str
    message: str
    entity_ids: dict = {}
    affected_entry_ids: list[int] = []


class ConflictResponse(BaseModel):
    conflicts: list[ConflictItem]
    hard_conflicts: int
    soft_conflicts: int


class ApplyChangeRequest(BaseModel):
    entry_id: int
    day_id: int
    period_id: int
    subject_id: int | None = None
    teacher_id: int | None = None
    room_id: int | None = None
    is_free: bool = False


class ValidateMoveRequest(BaseModel):
    entry_id: int
    target_day_id: int
    target_period_id: int
    swap_entry_id: int | None = None


class ValidateMoveResponse(BaseModel):
    valid: bool
    errors: list[str] = []


class RegenerateRequest(BaseModel):
    affected_entry_ids: list[int] = Field(default_factory=list)
    teacher_id: int | None = None
    preserve_locked: bool = True
    reason: str = ""


class SelectVersionRequest(BaseModel):
    version_id: int


# ── AI ──────────────────────────────────────────────────────────────────────


class PreferredPeriodRule(BaseModel):
    subject: str
    subject_id: int | None = None
    preferred_periods: list[int] = Field(default_factory=list)


class ParsedSchedulingInstruction(BaseModel):
    class_name: str | None = Field(default=None, alias="class")
    section: str | None = None
    teacher: str | None = None
    preferences: list[PreferredPeriodRule] = Field(default_factory=list)
    unavailable: list[dict] = Field(default_factory=list)
    notes: str = ""
    uncertainty: str = ""
    constraint_type: str = "preferred_periods"
    kind: ConstraintKind = ConstraintKind.SOFT
    weight: int = 8
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class ParseRuleRequest(BaseModel):
    instruction: str
    apply: bool = False


class ColumnMapping(BaseModel):
    source_column: str
    target_field: str
    confidence: float = Field(ge=0, le=1)
    uncertain: bool = False


class ExcelParseResult(BaseModel):
    entity_type: Literal["teachers", "subjects", "classes", "availability", "unknown"]
    mappings: list[ColumnMapping]
    sample_rows: list[dict] = Field(default_factory=list)
    needs_confirmation: bool = False
    notes: str = ""
    model_config = ConfigDict(extra="ignore")


class ConflictExplanation(BaseModel):
    summary: str
    causes: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    affected_entities: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="ignore")


class ImprovementSuggestion(BaseModel):
    title: str
    detail: str
    impact: str = "medium"
    related_constraint: str = ""
    model_config = ConfigDict(extra="ignore")


class ImprovementResponse(BaseModel):
    suggestions: list[ImprovementSuggestion] = Field(default_factory=list)
    overall: str = ""
    model_config = ConfigDict(extra="ignore")


class ModifyInstruction(BaseModel):
    intent: Literal[
        "mark_unavailable",
        "prefer_period",
        "swap",
        "lock",
        "regenerate_affected",
        "add_rule",
        "unknown",
    ] = "unknown"
    teacher: str | None = None
    teacher_id: int | None = None
    class_name: str | None = None
    section: str | None = None
    subject: str | None = None
    day: str | None = None
    period: int | None = None
    payload: dict = Field(default_factory=dict)
    reply: str = ""
    confidence: float = 0
    uncertainty: str = ""
    requires_solver: bool = False
    model_config = ConfigDict(extra="ignore")


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None
    confirm_action: bool = False


class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    action: ModifyInstruction | None = None
    applied: bool = False
    affected_count: int = 0


class ExplainConflictRequest(BaseModel):
    conflict: dict
    extra_context: str = ""


class ImportConfirmRequest(BaseModel):
    entity_type: str
    mappings: list[ColumnMapping]
    rows: list[dict]


# ── Notifications / dashboard ───────────────────────────────────────────────


class NotificationOut(ORMModel):
    id: int
    title: str
    body: str
    channel: NotificationChannel
    is_read: bool
    payload: dict = {}
    created_at: datetime | None = None


class DashboardOut(BaseModel):
    total_classes: int
    total_sections: int
    total_teachers: int
    total_subjects: int
    total_rooms: int
    timetable_status: str
    last_generated: datetime | None
    hard_conflicts: int
    soft_preference_score: float
    teacher_workload: list[dict]
    selected_version_id: int | None = None
