"""Domain enumerations shared by the models, schemas and mobile clients."""

from enum import StrEnum


class UserRole(StrEnum):
    FLEET_MANAGER = "FLEET_MANAGER"
    DRIVER = "DRIVER"


class VehicleStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    ON_TRIP = "ON_TRIP"
    IN_MAINTENANCE = "IN_MAINTENANCE"
    INACTIVE = "INACTIVE"


class FuelType(StrEnum):
    PETROL = "PETROL"
    DIESEL = "DIESEL"
    CNG = "CNG"
    ELECTRIC = "ELECTRIC"
    HYBRID = "HYBRID"


class VehicleType(StrEnum):
    TRUCK = "TRUCK"
    VAN = "VAN"
    CAR = "CAR"
    BIKE = "BIKE"
    BUS = "BUS"


class DriverStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class TripStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class IncidentSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class MaintenanceType(StrEnum):
    OIL_CHANGE = "OIL_CHANGE"
    BRAKE_SERVICE = "BRAKE_SERVICE"
    TYRE_REPLACEMENT = "TYRE_REPLACEMENT"
    ENGINE_SERVICE = "ENGINE_SERVICE"
    GENERAL_INSPECTION = "GENERAL_INSPECTION"
    OTHER = "OTHER"


class NotificationCategory(StrEnum):
    MAINTENANCE_DUE = "MAINTENANCE_DUE"
    INSURANCE_EXPIRY = "INSURANCE_EXPIRY"
    LICENSE_EXPIRY = "LICENSE_EXPIRY"
    TRIP_ASSIGNED = "TRIP_ASSIGNED"
    TRIP_COMPLETED = "TRIP_COMPLETED"
    INCIDENT_REPORTED = "INCIDENT_REPORTED"
