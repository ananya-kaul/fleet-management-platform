from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import FuelType, VehicleStatus, VehicleType


class VehicleBase(BaseModel):
    registration_number: str = Field(min_length=4, max_length=32)
    vehicle_type: VehicleType
    make: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=60)
    year: int = Field(ge=1950, le=2100)
    fuel_type: FuelType
    current_mileage: float = Field(default=0, ge=0)
    insurance_expiry: date | None = None
    registration_expiry: date | None = None

    @field_validator("registration_number")
    @classmethod
    def normalise_registration(cls, value: str) -> str:
        # Registrations are compared for uniqueness, so store one canonical form.
        return value.strip().upper().replace(" ", "-")


class VehicleCreate(VehicleBase):
    status: VehicleStatus = VehicleStatus.AVAILABLE


class VehicleUpdate(BaseModel):
    vehicle_type: VehicleType | None = None
    make: str | None = Field(default=None, min_length=1, max_length=60)
    model: str | None = Field(default=None, min_length=1, max_length=60)
    year: int | None = Field(default=None, ge=1950, le=2100)
    fuel_type: FuelType | None = None
    current_mileage: float | None = Field(default=None, ge=0)
    status: VehicleStatus | None = None
    insurance_expiry: date | None = None
    registration_expiry: date | None = None


class VehicleRead(VehicleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: VehicleStatus
    is_active: bool


class VehicleSummary(BaseModel):
    """Compact projection embedded in trip and assignment payloads."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    registration_number: str
    make: str
    model: str
    status: VehicleStatus
