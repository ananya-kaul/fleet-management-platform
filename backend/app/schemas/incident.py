from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IncidentSeverity, IncidentStatus
from app.schemas.driver import DriverSummary
from app.schemas.vehicle import VehicleSummary


class IncidentCreate(BaseModel):
    vehicle_id: int
    trip_id: int | None = None
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    severity: IncidentSeverity
    reported_at: datetime | None = None


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    severity: IncidentSeverity | None = None
    assigned_to_user_id: int | None = None
    resolution_notes: str | None = Field(default=None, max_length=1000)


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    trip_id: int | None
    reported_by_driver_id: int | None
    assigned_to_user_id: int | None
    title: str
    description: str | None
    severity: IncidentSeverity
    status: IncidentStatus
    resolution_notes: str | None
    reported_at: datetime
    resolved_at: datetime | None
    vehicle: VehicleSummary | None = None
    reported_by: DriverSummary | None = None
