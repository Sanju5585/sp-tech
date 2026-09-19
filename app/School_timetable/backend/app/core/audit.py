from sqlalchemy.orm import Session

from app.models.entities import AuditLog, User


def write_audit(
    db: Session,
    user: User | None,
    action: str,
    entity_type: str = "",
    entity_id: str | int = "",
    details: dict | None = None,
    school_id: int | None = None,
) -> None:
    db.add(
        AuditLog(
            school_id=school_id if school_id is not None else (user.school_id if user else None),
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details or {},
        )
    )
