from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import DriverStatus


class DriverBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(min_length=6, max_length=20)
    license_number: str = Field(min_length=4, max_length=40)
    license_expiry: date


class DriverCreate(DriverBase):
    status: DriverStatus = DriverStatus.ACTIVE
    # Optionally provision a login for the driver in the same request.
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class DriverUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone_number: str | None = Field(default=None, min_length=6, max_length=20)
    license_number: str | None = Field(default=None, min_length=4, max_length=40)
    license_expiry: date | None = None
    status: DriverStatus | None = None


class DriverRead(DriverBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: DriverStatus
    user_id: int | None = None
    assigned_vehicle_id: int | None = None
    assigned_vehicle_registration: str | None = None


class DriverSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone_number: str
    status: DriverStatus
