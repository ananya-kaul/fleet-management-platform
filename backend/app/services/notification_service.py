"""Creates in-app notification rows and hands them to the push dispatcher.

Push delivery is abstracted behind `push.send` so the transport (APNs / FCM)
can be swapped without touching the callers.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import Notification, NotificationCategory, User, UserRole
from app.services import push

logger = get_logger(__name__)


def notify_user(
    db: Session,
    *,
    user_id: int,
    category: NotificationCategory,
    title: str,
    body: str,
    reference: str | None = None,
    commit: bool = True,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        category=category,
        title=title,
        body=body,
        reference=reference,
    )
    db.add(notification)
    if commit:
        db.commit()
        db.refresh(notification)

    push.send(user_id=user_id, title=title, body=body, reference=reference)
    return notification


def notify_fleet_managers(
    db: Session,
    *,
    category: NotificationCategory,
    title: str,
    body: str,
    reference: str | None = None,
    commit: bool = True,
) -> list[Notification]:
    managers = list(
        db.scalars(
            select(User).where(
                User.role == UserRole.FLEET_MANAGER, User.is_active.is_(True)
            )
        )
    )
    return [
        notify_user(
            db,
            user_id=manager.id,
            category=category,
            title=title,
            body=body,
            reference=reference,
            commit=commit,
        )
        for manager in managers
    ]


def list_for_user(
    db: Session, user_id: int, *, unread_only: bool = False, limit: int = 50
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    return list(db.scalars(stmt.order_by(Notification.created_at.desc()).limit(limit)))


def mark_read(db: Session, user_id: int, notification_id: int) -> Notification | None:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
    )
    if notification is None:
        return None
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: int) -> int:
    rows = list(
        db.scalars(
            select(Notification).where(
                Notification.user_id == user_id, Notification.is_read.is_(False)
            )
        )
    )
    for row in rows:
        row.is_read = True
    db.commit()
    return len(rows)
