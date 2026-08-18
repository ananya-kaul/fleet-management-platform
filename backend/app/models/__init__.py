"""Importing every model here keeps Base.metadata complete for Alembic."""

from app.models.assignment import VehicleAssignment
from app.models.driver import Driver
from app.models.enums import (
    DriverStatus,
    FuelType,
    IncidentSeverity,
    IncidentStatus,
    MaintenanceType,
    NotificationCategory,
    TripStatus,
    UserRole,
    VehicleStatus,
    VehicleType,
)
from app.models.incident import Incident
from app.models.location import Location
from app.models.maintenance import MaintenanceRecord
from app.models.notification import Notification
from app.models.trip import Trip
from app.models.user import User
from app.models.vehicle import Vehicle

__all__ = [
    "Driver",
    "DriverStatus",
    "FuelType",
    "Incident",
    "IncidentSeverity",
    "IncidentStatus",
    "Location",
    "MaintenanceRecord",
    "MaintenanceType",
    "Notification",
    "NotificationCategory",
    "Trip",
    "TripStatus",
    "User",
    "UserRole",
    "Vehicle",
    "VehicleAssignment",
    "VehicleStatus",
    "VehicleType",
]
