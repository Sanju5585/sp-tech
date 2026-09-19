from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.entities import Role, RoleName, School, Teacher, User


def normalize_username(value: str) -> str:
    username = (value or "").strip()
    if len(username) < 3:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username must be at least 3 characters")
    if " " in username:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username cannot contain spaces")
    return username


def find_user_by_login(db: Session, ident: str) -> User | None:
    ident = ident.strip()
    if not ident:
        return None
    by_username = (
        db.query(User)
        .filter(func.lower(User.username) == ident.lower())
        .first()
    )
    if by_username:
        return by_username
    return db.query(User).filter(User.email == ident.lower()).first()


def assert_username_free(db: Session, username: str, exclude_id: int | None = None) -> None:
    q = db.query(User).filter(func.lower(User.username) == username.lower())
    if exclude_id is not None:
        q = q.filter(User.id != exclude_id)
    if q.first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")


def assert_email_free(db: Session, email: str, exclude_id: int | None = None) -> None:
    q = db.query(User).filter(User.email == email.lower())
    if exclude_id is not None:
        q = q.filter(User.id != exclude_id)
    if q.first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")


def placeholder_email(username: str, school: School | None) -> str:
    domain = f"{school.code}.school" if school else "sanjivani.app"
    return f"{username.lower()}@{domain}"


def role_row(db: Session, name: RoleName) -> Role:
    row = db.query(Role).filter(Role.name == name).first()
    if row is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Role {name.value} is missing")
    return row


def create_login_user(
    db: Session,
    *,
    school: School | None,
    role: RoleName,
    full_name: str,
    username: str,
    password: str,
    email: str = "",
    phone: str = "",
) -> User:
    username = normalize_username(username)
    assert_username_free(db, username)
    email_value = (email or "").strip().lower() or placeholder_email(username, school)
    assert_email_free(db, email_value)
    user = User(
        school_id=school.id if school else None,
        role_id=role_row(db, role).id,
        username=username,
        email=email_value,
        hashed_password=hash_password(password),
        full_name=full_name.strip(),
        phone=phone or "",
    )
    db.add(user)
    db.flush()
    return user


def maybe_create_teacher_login(
    db: Session,
    *,
    school: School,
    teacher: Teacher,
    username: str,
    password: str,
    email: str = "",
) -> User | None:
    if not username or not password:
        return None
    user = create_login_user(
        db,
        school=school,
        role=RoleName.TEACHER,
        full_name=teacher.name,
        username=username,
        password=password,
        email=email or teacher.email,
        phone=teacher.phone,
    )
    teacher.user_id = user.id
    if not teacher.email:
        teacher.email = user.email
    return user
