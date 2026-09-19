from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.core.accounts import create_login_user, find_user_by_login
from app.core.audit import write_audit
from app.core.portal_sso import verify_portal_sso_token
from app.core.rbac import get_current_user, require_roles
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.database import get_db
from app.models.entities import Role, RoleName, School, Teacher, User
from app.schemas import (
    LoginRequest,
    PortalSsoRequest,
    RefreshRequest,
    RegisterRequest,
    StaffUserIn,
    TokenResponse,
    UserOut,
    UserStatusIn,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
SuperAdmin = require_roles(RoleName.SUPER_ADMIN)
SchoolStaffAdmin = require_roles(RoleName.SUPER_ADMIN, RoleName.SCHOOL_ADMIN)


def _tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        role=user.role.name,
        school_id=user.school_id,
        user_id=user.id,
        full_name=user.full_name,
        teacher_id=user.teacher.id if getattr(user, "teacher", None) else None,
    )


@router.post("/register", response_model=TokenResponse)
def register(_body: RegisterRequest):
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Public registration is closed. Ask the super admin to create a school admin account.",
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    ident = body.email.strip()
    password = body.password.strip()
    user = find_user_by_login(db, ident)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.teacher))
        .filter(User.id == user.id)
        .first()
    )
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    user.last_login_at = datetime.utcnow()
    db.commit()
    return _tokens(user)


@router.post("/portal-sso", response_model=TokenResponse)
def portal_sso(body: PortalSsoRequest, db: Session = Depends(get_db)):
    payload = verify_portal_sso_token(body.token.strip())
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired portal token")
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.teacher))
        .join(Role)
        .filter(Role.name == RoleName.SUPER_ADMIN)
        .first()
    )
    if user is None:
        user = find_user_by_login(db, settings.bootstrap_super_username)
        if user:
            user = (
                db.query(User)
                .options(joinedload(User.role), joinedload(User.teacher))
                .filter(User.id == user.id)
                .first()
            )
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Timetable super admin is not ready")
    user.last_login_at = datetime.utcnow()
    db.commit()
    return _tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    user_id = decode_token(body.refresh_token, "refresh")
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = db.get(User, user_id, options=[joinedload(User.role), joinedload(User.teacher)])
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return _tokens(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.from_user(user)


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(SchoolStaffAdmin),
    x_school_id: int | None = Header(default=None, alias="X-School-Id"),
):
    query = db.query(User).options(joinedload(User.role))
    if user.role.name == RoleName.SUPER_ADMIN:
        if x_school_id:
            query = query.filter(User.school_id == x_school_id)
        else:
            query = query.filter(User.school_id.is_not(None))
    else:
        query = query.filter(User.school_id == user.school_id)
    return [UserOut.from_user(u) for u in query.order_by(User.full_name).all()]


@router.post("/users", response_model=UserOut)
def create_user(
    body: StaffUserIn,
    db: Session = Depends(get_db),
    actor: User = Depends(SchoolStaffAdmin),
):
    role = RoleName(body.role)
    if role == RoleName.SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot create a super admin")
    if actor.role.name == RoleName.SCHOOL_ADMIN and role == RoleName.SCHOOL_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the super admin can create school admins")
    if actor.role.name == RoleName.SUPER_ADMIN:
        if role != RoleName.SCHOOL_ADMIN:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Super admin creates school admin accounts only")
        if not body.school_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "school_id is required")
        school = db.get(School, body.school_id)
        if school is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "School not found")
    else:
        school = db.get(School, actor.school_id)
        if school is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not assigned to a school")

    created = create_login_user(
        db,
        school=school,
        role=role,
        full_name=body.full_name,
        username=body.username,
        password=body.password,
        email=body.email,
        phone=body.phone,
    )
    if role == RoleName.TEACHER:
        emp = (body.employee_id or created.username).strip()
        existing = (
            db.query(Teacher)
            .filter(Teacher.school_id == school.id, Teacher.employee_id == emp)
            .first()
        )
        if existing:
            if existing.user_id and existing.user_id != created.id:
                raise HTTPException(status.HTTP_409_CONFLICT, "That employee ID already has a login")
            existing.user_id = created.id
        else:
            db.add(
                Teacher(
                    school_id=school.id,
                    user_id=created.id,
                    name=body.full_name,
                    employee_id=emp,
                    email=created.email,
                    phone=body.phone,
                )
            )
    write_audit(db, actor, "create_user", "user", created.id, {"role": role.value}, school.id)
    db.commit()
    created = db.get(User, created.id, options=[joinedload(User.role)])
    return UserOut.from_user(created)


@router.put("/users/{user_id}/status", response_model=UserOut)
def set_user_status(
    user_id: int,
    body: UserStatusIn,
    db: Session = Depends(get_db),
    actor: User = Depends(SchoolStaffAdmin),
):
    target = db.get(User, user_id, options=[joinedload(User.role)])
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if target.role.name == RoleName.SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot disable the super admin")
    if actor.role.name == RoleName.SCHOOL_ADMIN:
        if target.school_id != actor.school_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-school access denied")
        if target.role.name == RoleName.SCHOOL_ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "School admins cannot disable other admins")
    target.is_active = body.is_active
    write_audit(db, actor, "set_user_status", "user", target.id, {"is_active": body.is_active}, target.school_id)
    db.commit()
    db.refresh(target)
    return UserOut.from_user(target)
