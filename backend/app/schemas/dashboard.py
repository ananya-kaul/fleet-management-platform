from datetime import date

from pydantic import BaseModel

from app.schemas.incident import IncidentRead
from app.schemas.maintenance import MaintenanceDueItem


class ExpiringDocument(BaseModel):
    vehicle_id: int | None = None
    driver_id: int | None = None
    subject: str
    document: str
    expires_on: date
    days_remaining: int


class DashboardResponse(BaseModel):
    total_vehicles: int
    available_vehicles: int
    vehicles_on_trip: int
    vehicles_in_maintenance: int
    inactive_vehicles: int

    total_drivers: int
    active_drivers: int

    active_trips: int
    scheduled_trips: int
    completed_trips_today: int
    distance_today_km: float

    maintenance_due_count: int
    expiring_documents_count: int
    open_incidents: int

    maintenance_due: list[MaintenanceDueItem]
    expiring_documents: list[ExpiringDocument]
    recent_incidents: list[IncidentRead]
