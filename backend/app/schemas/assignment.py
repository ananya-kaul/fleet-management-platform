from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.driver import DriverSummary
from app.schemas.vehicle import VehicleSummary


class AssignmentCreate(BaseModel):
    vehicle_id: int
    driver_id: int
    start_date: date
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def check_range(self) -> "AssignmentCreate":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    driver_id: int
    start_date: date
    end_date: date | None
    is_active: bool
    notes: str | None
    vehicle: VehicleSummary | None = None
    driver: DriverSummary | None = None
