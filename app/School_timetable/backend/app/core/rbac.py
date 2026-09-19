from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.core.security import decode_token
from app.database import get_db
from app.models.entities import RoleName, School, User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = decode_token(creds.credentials, "access")
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, user_id, options=[joinedload(User.role), joinedload(User.teacher)])
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inactive user")
    return user


def require_roles(*roles: RoleName):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role.name not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return checker


def resolve_school_id(
    user: User,
    x_school_id: int | None = None,
) -> int:
    if user.role.name == RoleName.SUPER_ADMIN:
        if x_school_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Super admin must provide X-School-Id",
            )
        return x_school_id
    if user.school_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not assigned to a school")
    return user.school_id


def get_tenant_school_id(
    user: User = Depends(get_current_user),
    x_school_id: int | None = Header(default=None, alias="X-School-Id"),
) -> int:
    return resolve_school_id(user, x_school_id)


def get_school(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_tenant_school_id),
) -> School:
    school = db.get(School, school_id)
    if school is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "School not found")
    return school


def assert_school_entity(entity, school_id: int, name: str = "Resource") -> None:
    if entity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{name} not found")
    if getattr(entity, "school_id", None) != school_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-school access denied")
