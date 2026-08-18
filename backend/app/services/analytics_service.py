"""Fleet analytics: utilisation, driver performance and cost per kilometre."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Driver, Incident, MaintenanceRecord, Trip, TripStatus, Vehicle
from app.schemas.analytics import DriverPerformance, FleetAnalytics, VehicleUtilisation


def build_analytics(db: Session, *, period_days: int = 30) -> FleetAnalytics:
    since = datetime.now(timezone.utc) - timedelta(days=period_days)

    vehicles = list(db.scalars(select(Vehicle)))
    vehicle_rows: list[VehicleUtilisation] = []
    total_distance = 0.0
    total_cost = 0.0

    for vehicle in vehicles:
        trips = list(
            db.scalars(
                select(Trip).where(
                    Trip.vehicle_id == vehicle.id,
                    Trip.status == TripStatus.COMPLETED,
                    Trip.actual_end >= since,
                )
            )
        )
        distance = sum(float(trip.distance_km or 0) for trip in trips)
        cost = float(
            db.scalar(
                select(func.coalesce(func.sum(MaintenanceRecord.cost), 0)).where(
                    MaintenanceRecord.vehicle_id == vehicle.id,
                    MaintenanceRecord.service_date >= since.date(),
                )
            )
            or 0
        )
        days_on_trip = len(
            {trip.actual_start.date() for trip in trips if trip.actual_start is not None}
        )

        total_distance += distance
        total_cost += cost
        vehicle_rows.append(
            VehicleUtilisation(
                vehicle_id=vehicle.id,
                registration_number=vehicle.registration_number,
                total_trips=len(trips),
                total_distance_km=round(distance, 2),
                maintenance_cost=round(cost, 2),
                cost_per_km=round(cost / distance, 4) if distance > 0 else None,
                days_on_trip=days_on_trip,
            )
        )

    driver_rows = [
        driver_performance(db, driver.id, period_days=period_days)
        for driver in db.scalars(select(Driver))
    ]

    return FleetAnalytics(
        period_days=period_days,
        total_distance_km=round(total_distance, 2),
        total_maintenance_cost=round(total_cost, 2),
        average_cost_per_km=(
            round(total_cost / total_distance, 4) if total_distance > 0 else None
        ),
        vehicles=sorted(vehicle_rows, key=lambda row: row.total_distance_km, reverse=True),
        drivers=sorted(driver_rows, key=lambda row: row.total_distance_km, reverse=True),
    )


def driver_performance(db: Session, driver_id: int, *, period_days: int = 30) -> DriverPerformance:
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    driver = db.get(Driver, driver_id)
    name = driver.name if driver else f"Driver {driver_id}"

    trips = list(
        db.scalars(
            select(Trip).where(Trip.driver_id == driver_id, Trip.scheduled_start >= since)
        )
    )
    completed = [trip for trip in trips if trip.status == TripStatus.COMPLETED]
    distance = sum(float(trip.distance_km or 0) for trip in completed)

    durations = [
        (trip.actual_end - trip.actual_start).total_seconds() / 60
        for trip in completed
        if trip.actual_start is not None and trip.actual_end is not None
    ]

    incidents = db.scalar(
        select(func.count())
        .select_from(Incident)
        .where(Incident.reported_by_driver_id == driver_id, Incident.reported_at >= since)
    ) or 0

    return DriverPerformance(
        driver_id=driver_id,
        name=name,
        total_trips=len(trips),
        completed_trips=len(completed),
        total_distance_km=round(distance, 2),
        average_trip_duration_minutes=(
            round(sum(durations) / len(durations), 1) if durations else None
        ),
        incidents_reported=incidents,
    )
