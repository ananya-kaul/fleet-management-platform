"""Vehicle CRUD with registration uniqueness and status guards."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import Trip, TripStatus, Vehicle, VehicleStatus
from app.schemas.vehicle import VehicleCreate, VehicleUpdate


def get_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise NotFoundError(f"Vehicle {vehicle_id} was not found")
    return vehicle


def create_vehicle(db: Session, payload: VehicleCreate) -> Vehicle:
    existing = db.scalar(
        select(Vehicle).where(Vehicle.registration_number == payload.registration_number)
    )
    if existing is not None:
        raise ConflictError(
            f"A vehicle with registration {payload.registration_number} already exists",
            code="duplicate_registration",
        )

    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def update_vehicle(db: Session, vehicle_id: int, payload: VehicleUpdate) -> Vehicle:
    vehicle = get_vehicle(db, vehicle_id)
    changes = payload.model_dump(exclude_unset=True)

    new_status = changes.get("status")
    if new_status is not None and new_status != vehicle.status:
        _guard_status_change(db, vehicle, new_status)

    for field, value in changes.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return vehicle


def _guard_status_change(db: Session, vehicle: Vehicle, new_status: VehicleStatus) -> None:
    """A vehicle on an active trip cannot be pulled out from under the driver."""
    if vehicle.status != VehicleStatus.ON_TRIP:
        return
    if new_status == VehicleStatus.ON_TRIP:
        return

    active_trip = db.scalar(
        select(Trip).where(
            Trip.vehicle_id == vehicle.id,
            Trip.status.in_([TripStatus.STARTED, TripStatus.IN_PROGRESS]),
        )
    )
    if active_trip is not None:
        raise ConflictError(
            f"Vehicle is on active trip {active_trip.trip_code}; complete or cancel it first",
            code="vehicle_on_active_trip",
        )


def deactivate_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = get_vehicle(db, vehicle_id)
    _guard_status_change(db, vehicle, VehicleStatus.INACTIVE)
    vehicle.is_active = False
    vehicle.status = VehicleStatus.INACTIVE
    db.commit()
    db.refresh(vehicle)
    return vehicle


def activate_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = get_vehicle(db, vehicle_id)
    vehicle.is_active = True
    if vehicle.status == VehicleStatus.INACTIVE:
        vehicle.status = VehicleStatus.AVAILABLE
    db.commit()
    db.refresh(vehicle)
    return vehicle


def list_vehicles(
    db: Session,
    *,
    search: str | None = None,
    status: VehicleStatus | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Vehicle], int]:
    stmt = select(Vehicle)
    count_stmt = select(func.count()).select_from(Vehicle)

    filters = []
    if search:
        pattern = f"%{search.strip().lower()}%"
        filters.append(
            or_(
                func.lower(Vehicle.registration_number).like(pattern),
                func.lower(Vehicle.make).like(pattern),
                func.lower(Vehicle.model).like(pattern),
            )
        )
    if status is not None:
        filters.append(Vehicle.status == status)
    if is_active is not None:
        filters.append(Vehicle.is_active.is_(is_active))

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = db.scalar(count_stmt) or 0
    rows = list(
        db.scalars(stmt.order_by(Vehicle.registration_number).limit(limit).offset(offset))
    )
    return rows, total
