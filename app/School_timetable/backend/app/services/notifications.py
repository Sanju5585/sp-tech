from sqlalchemy.orm import Session, joinedload

from app.models.entities import Notification, NotificationChannel, Teacher, User


def notify(
    db: Session,
    school_id: int,
    user_id: int,
    title: str,
    body: str,
    payload: dict | None = None,
    channel: NotificationChannel = NotificationChannel.IN_APP,
) -> Notification:
    n = Notification(
        school_id=school_id,
        user_id=user_id,
        title=title,
        body=body,
        channel=channel,
        payload=payload or {},
    )
    db.add(n)
    return n


def notify_teacher_changes(
    db: Session,
    school_id: int,
    teacher_id: int,
    title: str,
    body: str,
    payload: dict | None = None,
) -> None:
    teacher = db.get(Teacher, teacher_id)
    if teacher and teacher.user_id:
        notify(db, school_id, teacher.user_id, title, body, payload)


def notify_school_admins(
    db: Session,
    school_id: int,
    title: str,
    body: str,
    payload: dict | None = None,
) -> None:
    users = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.school_id == school_id, User.is_active.is_(True))
        .all()
    )
    for u in users:
        if u.role and u.role.name.value in ("school_admin", "super_admin"):
            notify(db, school_id, u.id, title, body, payload)
