from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.errors import NotFoundError
from app.schemas.common import Message
from app.schemas.notification import DeviceTokenRegister, NotificationRead
from app.services import notification_service, push

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    db: DbSession, user: CurrentUser, unread_only: bool = False
) -> list[NotificationRead]:
    rows = notification_service.list_for_user(db, user.id, unread_only=unread_only)
    return [NotificationRead.model_validate(row) for row in rows]


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(notification_id: int, db: DbSession, user: CurrentUser) -> NotificationRead:
    row = notification_service.mark_read(db, user.id, notification_id)
    if row is None:
        raise NotFoundError(f"Notification {notification_id} was not found")
    return NotificationRead.model_validate(row)


@router.post("/read-all", response_model=Message)
def mark_all_read(db: DbSession, user: CurrentUser) -> Message:
    count = notification_service.mark_all_read(db, user.id)
    return Message(detail=f"Marked {count} notifications as read")


@router.post("/devices", response_model=Message)
def register_device(payload: DeviceTokenRegister, user: CurrentUser) -> Message:
    push.register_device(user.id, payload.platform, payload.token)
    return Message(detail="Device registered for push notifications")


@router.delete("/devices/{token}", response_model=Message)
def unregister_device(token: str, user: CurrentUser) -> Message:
    push.unregister_device(user.id, token)
    return Message(detail="Device unregistered")
