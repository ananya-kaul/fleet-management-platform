from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationCategory


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: NotificationCategory
    title: str
    body: str
    is_read: bool
    reference: str | None
    created_at: datetime


class DeviceTokenRegister(BaseModel):
    """Accepted so the mobile clients can register for push delivery."""

    token: str
    platform: str
