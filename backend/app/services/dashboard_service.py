"""Aggregations powering the fleet manager dashboard."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Driver,
    DriverStatus,
    Incident,
    IncidentStatus,
    Trip,
    TripStatus,
    Vehicle,
    VehicleStatus,
)
from app.schemas.dashboard import DashboardResponse, ExpiringDocument
from app.schemas.incident import IncidentRead
from app.services import incident_service, maintenance_service


def _count_vehicles(db: Session, status: VehicleStatus) -> int:
    return db.scalar(
        select(func.count()).select_from(Vehicle).where(Vehicle.status == status)
    ) or 0


def _today_bounds() -> tuple[datetime, datetime]:
    today = date.today()
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def build_dashboard(db: Session) -> DashboardResponse:
    day_start, day_end = _today_bounds()

    total_vehicles = db.scalar(select(func.count()).select_from(Vehicle)) or 0
    total_drivers = db.scalar(select(func.count()).select_from(Driver)) or 0
    active_drivers = db.scalar(
        select(func.count()).select_from(Driver).where(Driver.status == DriverStatus.ACTIVE)
    ) or 0

    active_trips = db.scalar(
        select(func.count())
        .select_from(Trip)
        .where(Trip.status.in_([TripStatus.STARTED, TripStatus.IN_PROGRESS]))
    ) or 0
    scheduled_trips = db.scalar(
        select(func.count()).select_from(Trip).where(Trip.status == TripStatus.SCHEDULED)
    ) or 0

    completed_today = db.scalar(
        select(func.count())
        .select_from(Trip)
        .where(
            Trip.status == TripStatus.COMPLETED,
            Trip.actual_end >= day_start,
            Trip.actual_end < day_end,
        )
    ) or 0
    distance_today = db.scalar(
        select(func.coalesce(func.sum(Trip.distance_km), 0)).where(
            Trip.status == TripStatus.COMPLETED,
            Trip.actual_end >= day_start,
            Trip.actual_end < day_end,
        )
    ) or 0

    maintenance_due = maintenance_service.vehicles_due(db)
    expiring = expiring_documents(db)
    open_incidents = db.scalar(
        select(func.count())
        .select_from(Incident)
        .where(Incident.status != IncidentStatus.RESOLVED)
    ) or 0
    recent_incidents, _ = incident_service.list_incidents(db, limit=5)

    return DashboardResponse(
        total_vehicles=total_vehicles,
        available_vehicles=_count_vehicles(db, VehicleStatus.AVAILABLE),
        vehicles_on_trip=_count_vehicles(db, VehicleStatus.ON_TRIP),
        vehicles_in_maintenance=_count_vehicles(db, VehicleStatus.IN_MAINTENANCE),
        inactive_vehicles=_count_vehicles(db, VehicleStatus.INACTIVE),
        total_drivers=total_drivers,
        active_drivers=active_drivers,
        active_trips=active_trips,
        scheduled_trips=scheduled_trips,
        completed_trips_today=completed_today,
        distance_today_km=float(distance_today),
        maintenance_due_count=len(maintenance_due),
        expiring_documents_count=len(expiring),
        open_incidents=open_incidents,
        maintenance_due=maintenance_due,
        expiring_documents=expiring,
        recent_incidents=[IncidentRead.model_validate(row) for row in recent_incidents],
    )


def expiring_documents(db: Session, *, window_days: int | None = None) -> list[ExpiringDocument]:
    """Vehicle insurance/registration and driver licences falling due soon.

    Already-expired documents are included with a negative days_remaining so
    they stay visible rather than dropping off the list.
    """
    horizon = window_days if window_days is not None else settings.document_expiry_window_days
    today = date.today()
    cutoff = today + timedelta(days=horizon)
    results: list[ExpiringDocument] = []

    vehicles = list(db.scalars(select(Vehicle).where(Vehicle.is_active.is_(True))))
    for vehicle in vehicles:
        for label, expiry in (
            ("Insurance", vehicle.insurance_expiry),
            ("Registration", vehicle.registration_expiry),
        ):
            if expiry is not None and expiry <= cutoff:
                results.append(
                    ExpiringDocument(
                        vehicle_id=vehicle.id,
                        subject=vehicle.registration_number,
                        document=label,
                        expires_on=expiry,
                        days_remaining=(expiry - today).days,
                    )
                )

    drivers = list(
        db.scalars(select(Driver).where(Driver.status == DriverStatus.ACTIVE))
    )
    for driver in drivers:
        if driver.license_expiry <= cutoff:
            results.append(
                ExpiringDocument(
                    driver_id=driver.id,
                    subject=driver.name,
                    document="Driving licence",
                    expires_on=driver.license_expiry,
                    days_remaining=(driver.license_expiry - today).days,
                )
            )

    return sorted(results, key=lambda item: item.expires_on)
