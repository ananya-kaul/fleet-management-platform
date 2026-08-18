from pydantic import BaseModel


class DriverPerformance(BaseModel):
    driver_id: int
    name: str
    total_trips: int
    completed_trips: int
    total_distance_km: float
    average_trip_duration_minutes: float | None
    incidents_reported: int


class VehicleUtilisation(BaseModel):
    vehicle_id: int
    registration_number: str
    total_trips: int
    total_distance_km: float
    maintenance_cost: float
    cost_per_km: float | None
    days_on_trip: int


class FleetAnalytics(BaseModel):
    period_days: int
    total_distance_km: float
    total_maintenance_cost: float
    average_cost_per_km: float | None
    vehicles: list[VehicleUtilisation]
    drivers: list[DriverPerformance]
