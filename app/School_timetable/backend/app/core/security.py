from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    payload = {
        "sub": subject,
        "type": token_type,
        "exp": datetime.utcnow() + expires_delta,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: int) -> str:
    return create_token(
        str(user_id),
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: int) -> str:
    return create_token(
        str(user_id),
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError, TypeError):
        return None
