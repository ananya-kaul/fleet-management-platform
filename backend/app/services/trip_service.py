"""Trip lifecycle.

Legal status transitions:

    SCHEDULED   -> STARTED | CANCELLED
    STARTED     -> IN_PROGRESS | COMPLETED | CANCELLED
    IN_PROGRESS -> COMPLETED | CANCELLED
    COMPLETED   -> (terminal)
    CANCELLED   -> (terminal)
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models import (
    Driver,
    DriverStatus,
    NotificationCategory,
    Trip,
    TripStatus,
    Vehicle,
    VehicleStatus,
)
from app.schemas.trip import TripCompleteRequest, TripCreate, TripStartRequest, TripUpdate
from app.services import notification_service

logger = get_logger(__name__)

ALLOWED_TRANSITIONS: dict[TripStatus, set[TripStatus]] = {
    TripStatus.SCHEDULED: {TripStatus.STARTED, TripStatus.CANCELLED},
    TripStatus.STARTED: {
        TripStatus.IN_PROGRESS,
        TripStatus.COMPLETED,
        TripStatus.CANCELLED,
    },
    TripStatus.IN_PROGRESS: {TripStatus.COMPLETED, TripStatus.CANCELLED},
    TripStatus.COMPLETED: set(),
    TripStatus.CANCELLED: set(),
}

ACTIVE_STATUSES = (TripStatus.STARTED, TripStatus.IN_PROGRESS)


def assert_transition_allowed(current: TripStatus, target: TripStatus) -> None:
    if target == current:
        raise ConflictError(f"Trip is already {current}", code="invalid_transition")
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ConflictError(
            f"Cannot move a trip from {current} to {target}", code="invalid_transition"
        )


def _next_trip_code(db: Session) -> str:
    highest = db.scalar(select(func.max(Trip.id))) or 0
    return f"TRP{1000 + highest + 1}"


def get_trip(db: Session, trip_id: int) -> Trip:
    trip = db.scalar(
        select(Trip)
        .options(selectinload(Trip.vehicle), selectinload(Trip.driver))
        .where(Trip.id == trip_id)
    )
    if trip is None:
        raise NotFoundError(f"Trip {trip_id} was not found")
    return trip


def create_trip(db: Session, payload: TripCreate) -> Trip:
    vehicle = db.get(Vehicle, payload.vehicle_id)
    if vehicle is None:
        raise NotFoundError(f"Vehicle {payload.vehicle_id} was not found")
    driver = db.get(Driver, payload.driver_id)
    if driver is None:
        raise NotFoundError(f"Driver {payload.driver_id} was not found")

    if not vehicle.is_active or vehicle.status == VehicleStatus.INACTIVE:
        raise ConflictError("Cannot schedule a trip on an inactive vehicle",
                            code="vehicle_inactive")
    if vehicle.status == VehicleStatus.IN_MAINTENANCE:
        raise ConflictError("Vehicle is in maintenance", code="vehicle_in_maintenance")
    if driver.status != DriverStatus.ACTIVE:
        raise ConflictError("Cannot schedule a trip for an inactive driver",
                            code="driver_inactive")

    _assert_no_schedule_clash(db, payload)

    trip = Trip(
        trip_code=_next_trip_code(db),
        **payload.model_dump(),
    )
    db.add(trip)
    db.flush()

    if driver.user_id is not None:
        notification_service.notify_user(
            db,
            user_id=driver.user_id,
            category=NotificationCategory.TRIP_ASSIGNED,
            title="New trip assigned",
            body=f"{trip.trip_code}: {trip.source} to {trip.destination}",
            reference=f"trip:{trip.id}",
            commit=False,
        )

    db.commit()
    db.refresh(trip)
    logger.info("Created trip %s for vehicle=%s driver=%s",
                trip.trip_code, trip.vehicle_id, trip.driver_id)
    return trip


def _assert_no_schedule_clash(db: Session, payload: TripCreate) -> None:
    """Reject a trip that overlaps an existing open trip for the same vehicle or driver."""
    open_statuses = [TripStatus.SCHEDULED, *ACTIVE_STATUSES]
    clash = db.scalar(
        select(Trip).where(
            Trip.status.in_(open_statuses),
            Trip.scheduled_start < payload.scheduled_end,
            Trip.scheduled_end > payload.scheduled_start,
            (Trip.vehicle_id == payload.vehicle_id)
            | (Trip.driver_id == payload.driver_id),
        )
    )
    if clash is None:
        return

    subject = "Vehicle" if clash.vehicle_id == payload.vehicle_id else "Driver"
    raise ConflictError(
        f"{subject} is already booked on trip {clash.trip_code} for that window",
        code="trip_schedule_conflict",
    )


def update_trip(db: Session, trip_id: int, payload: TripUpdate) -> Trip:
    trip = get_trip(db, trip_id)
    if trip.status != TripStatus.SCHEDULED:
        raise ConflictError(
            "Only scheduled trips can be edited", code="trip_not_editable"
        )

    changes = payload.model_dump(exclude_unset=True)
    start = changes.get("scheduled_start", trip.scheduled_start)
    end = changes.get("scheduled_end", trip.scheduled_end)
    if end <= start:
        raise ValidationError("scheduled_end must be after scheduled_start")

    for field, value in changes.items():
        setattr(trip, field, value)

    db.commit()
    db.refresh(trip)
    return trip


def start_trip(db: Session, trip_id: int, payload: TripStartRequest) -> Trip:
    trip = get_trip(db, trip_id)
    assert_transition_allowed(trip.status, TripStatus.STARTED)

    vehicle = trip.vehicle
    if vehicle.status == VehicleStatus.ON_TRIP:
        raise ConflictError(
            "Vehicle is already on another trip", code="vehicle_on_active_trip"
        )
    if vehicle.status == VehicleStatus.IN_MAINTENANCE:
        raise ConflictError("Vehicle is in maintenance", code="vehicle_in_maintenance")

    trip.status = TripStatus.STARTED
    trip.actual_start = payload.started_at or datetime.now(timezone.utc)
    trip.start_odometer = payload.start_odometer
    trip.start_latitude = payload.start_latitude
    trip.start_longitude = payload.start_longitude

    vehicle.status = VehicleStatus.ON_TRIP
    db.commit()
    db.refresh(trip)
    logger.info("Trip %s started at odometer %s", trip.trip_code, payload.start_odometer)
    return trip


def complete_trip(db: Session, trip_id: int, payload: TripCompleteRequest) -> Trip:
    trip = get_trip(db, trip_id)
    assert_transition_allowed(trip.status, TripStatus.COMPLETED)

    if trip.start_odometer is None:
        raise ConflictError(
            "Trip has no starting odometer reading", code="missing_start_odometer"
        )
    if payload.end_odometer < float(trip.start_odometer):
        raise ValidationError(
            "Ending odometer cannot be lower than the starting odometer "
            f"({trip.start_odometer})"
        )

    trip.status = TripStatus.COMPLETED
    trip.actual_end = payload.completed_at or datetime.now(timezone.utc)
    trip.end_odometer = payload.end_odometer
    trip.end_latitude = payload.end_latitude
    trip.end_longitude = payload.end_longitude
    trip.distance_km = payload.end_odometer - float(trip.start_odometer)

    vehicle = trip.vehicle
    # Keep the odometer authoritative on the vehicle record.
    vehicle.current_mileage = max(float(vehicle.current_mileage), payload.end_odometer)
    if vehicle.status == VehicleStatus.ON_TRIP:
        vehicle.status = VehicleStatus.AVAILABLE

    notification_service.notify_fleet_managers(
        db,
        category=NotificationCategory.TRIP_COMPLETED,
        title=f"Trip {trip.trip_code} completed",
        body=(
            f"{vehicle.registration_number} arrived at {trip.destination} "
            f"- {trip.distance_km:.1f} km"
        ),
        reference=f"trip:{trip.id}",
        commit=False,
    )

    db.commit()
    db.refresh(trip)
    logger.info("Trip %s completed, distance=%s km", trip.trip_code, trip.distance_km)
    return trip


def change_status(db: Session, trip_id: int, target: TripStatus, reason: str | None = None) -> Trip:
    """Handles the transitions that are not /start or /complete."""
    trip = get_trip(db, trip_id)

    if target in (TripStatus.STARTED, TripStatus.COMPLETED):
        raise ConflictError(
            f"Use the dedicated /trips/{{id}}/{target.lower()} endpoint",
            code="use_dedicated_endpoint",
        )

    assert_transition_allowed(trip.status, target)
    trip.status = target

    if target == TripStatus.CANCELLED:
        trip.cancellation_reason = reason
        if trip.vehicle.status == VehicleStatus.ON_TRIP:
            trip.vehicle.status = VehicleStatus.AVAILABLE

    db.commit()
    db.refresh(trip)
    return trip


def list_trips(
    db: Session,
    *,
    status: TripStatus | None = None,
    vehicle_id: int | None = None,
    driver_id: int | None = None,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Trip], int]:
    stmt = select(Trip).options(selectinload(Trip.vehicle), selectinload(Trip.driver))
    count_stmt = select(func.count()).select_from(Trip)

    filters = []
    if status is not None:
        filters.append(Trip.status == status)
    if vehicle_id is not None:
        filters.append(Trip.vehicle_id == vehicle_id)
    if driver_id is not None:
        filters.append(Trip.driver_id == driver_id)
    if active_only:
        filters.append(Trip.status.in_(ACTIVE_STATUSES))

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = db.scalar(count_stmt) or 0
    rows = list(
        db.scalars(stmt.order_by(Trip.scheduled_start.desc()).limit(limit).offset(offset))
    )
    return rows, total
