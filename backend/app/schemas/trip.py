from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import TripStatus
from app.schemas.driver import DriverSummary
from app.schemas.vehicle import VehicleSummary


class TripCreate(BaseModel):
    vehicle_id: int
    driver_id: int
    source: str = Field(min_length=2, max_length=160)
    destination: str = Field(min_length=2, max_length=160)
    scheduled_start: datetime
    scheduled_end: datetime
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_schedule(self) -> "TripCreate":
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("scheduled_end must be after scheduled_start")
        return self


class TripUpdate(BaseModel):
    source: str | None = Field(default=None, min_length=2, max_length=160)
    destination: str | None = Field(default=None, min_length=2, max_length=160)
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)


class TripStartRequest(BaseModel):
    start_odometer: float = Field(ge=0)
    start_latitude: float = Field(ge=-90, le=90)
    start_longitude: float = Field(ge=-180, le=180)
    started_at: datetime | None = None


class TripCompleteRequest(BaseModel):
    end_odometer: float = Field(ge=0)
    end_latitude: float = Field(ge=-90, le=90)
    end_longitude: float = Field(ge=-180, le=180)
    completed_at: datetime | None = None


class TripStatusUpdate(BaseModel):
    status: TripStatus
    reason: str | None = Field(default=None, max_length=255)


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_code: str
    vehicle_id: int
    driver_id: int
    source: str
    destination: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: TripStatus
    notes: str | None

    actual_start: datetime | None
    start_latitude: float | None
    start_longitude: float | None
    start_odometer: float | None

    actual_end: datetime | None
    end_latitude: float | None
    end_longitude: float | None
    end_odometer: float | None

    distance_km: float | None
    cancellation_reason: str | None

    vehicle: VehicleSummary | None = None
    driver: DriverSummary | None = None
