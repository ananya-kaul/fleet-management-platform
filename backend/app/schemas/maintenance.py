from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MaintenanceType
from app.schemas.vehicle import VehicleSummary


class MaintenanceCreate(BaseModel):
    vehicle_id: int
    maintenance_type: MaintenanceType
    description: str | None = Field(default=None, max_length=500)
    service_date: date
    cost: float = Field(default=0, ge=0)
    odometer: float = Field(ge=0)
    next_service_date: date | None = None
    next_service_mileage: float | None = Field(default=None, ge=0)
    performed_by: str | None = Field(default=None, max_length=120)
    # Flip the vehicle into IN_MAINTENANCE when the work is booked in.
    set_vehicle_in_maintenance: bool = False


class MaintenanceUpdate(BaseModel):
    maintenance_type: MaintenanceType | None = None
    description: str | None = Field(default=None, max_length=500)
    service_date: date | None = None
    cost: float | None = Field(default=None, ge=0)
    odometer: float | None = Field(default=None, ge=0)
    next_service_date: date | None = None
    next_service_mileage: float | None = Field(default=None, ge=0)
    performed_by: str | None = Field(default=None, max_length=120)


class MaintenanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    maintenance_type: MaintenanceType
    description: str | None
    service_date: date
    cost: float
    odometer: float
    next_service_date: date | None
    next_service_mileage: float | None
    performed_by: str | None
    vehicle: VehicleSummary | None = None


class MaintenanceDueItem(BaseModel):
    vehicle_id: int
    registration_number: str
    reason: str
    due_date: date | None = None
    due_mileage: float | None = None
