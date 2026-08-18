"""Vehicle-driver assignment with overlap detection.

The core invariant is that a vehicle may not be held by two drivers over the
same dates, and a driver may not hold two vehicles over the same dates.
"""

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError
from app.models import (
    Driver,
    DriverStatus,
    Vehicle,
    VehicleAssignment,
    VehicleStatus,
)
from app.schemas.assignment import AssignmentCreate


def _overlapping(
    db: Session,
    *,
    column,
    entity_id: int,
    start: date,
    end: date | None,
    exclude_id: int | None = None,
) -> VehicleAssignment | None:
    """Find an active assignment for `entity_id` whose range intersects [start, end].

    Ranges [a1, a2] and [b1, b2] overlap when a1 <= b2 AND b1 <= a2. A null end
    date means "open ended", which is treated as +infinity on that side.
    """
    stmt = select(VehicleAssignment).where(
        column == entity_id,
        VehicleAssignment.is_active.is_(True),
    )
    if exclude_id is not None:
        stmt = stmt.where(VehicleAssignment.id != exclude_id)

    # existing.start <= new.end (or the new range is open ended)
    if end is not None:
        stmt = stmt.where(VehicleAssignment.start_date <= end)

    # existing.end >= new.start (or the existing range is open ended)
    stmt = stmt.where(
        or_(
            VehicleAssignment.end_date.is_(None),
            VehicleAssignment.end_date >= start,
        )
    )
    return db.scalar(stmt)


def create_assignment(db: Session, payload: AssignmentCreate) -> VehicleAssignment:
    vehicle = db.get(Vehicle, payload.vehicle_id)
    if vehicle is None:
        raise NotFoundError(f"Vehicle {payload.vehicle_id} was not found")
    driver = db.get(Driver, payload.driver_id)
    if driver is None:
        raise NotFoundError(f"Driver {payload.driver_id} was not found")

    if not vehicle.is_active or vehicle.status == VehicleStatus.INACTIVE:
        raise ConflictError(
            "Cannot assign an inactive vehicle", code="vehicle_inactive"
        )
    if driver.status != DriverStatus.ACTIVE:
        raise ConflictError("Cannot assign an inactive driver", code="driver_inactive")
    if driver.license_expiry < payload.start_date:
        raise ConflictError(
            "The driver's licence expires before the assignment starts",
            code="license_expired",
        )

    vehicle_clash = _overlapping(
        db,
        column=VehicleAssignment.vehicle_id,
        entity_id=payload.vehicle_id,
        start=payload.start_date,
        end=payload.end_date,
    )
    if vehicle_clash is not None:
        raise ConflictError(
            f"Vehicle {vehicle.registration_number} is already assigned to driver "
            f"{vehicle_clash.driver_id} for an overlapping period",
            code="vehicle_already_assigned",
        )

    driver_clash = _overlapping(
        db,
        column=VehicleAssignment.driver_id,
        entity_id=payload.driver_id,
        start=payload.start_date,
        end=payload.end_date,
    )
    if driver_clash is not None:
        raise ConflictError(
            f"Driver {driver.name} already holds vehicle {driver_clash.vehicle_id} "
            "for an overlapping period",
            code="driver_already_assigned",
        )

    assignment = VehicleAssignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def end_assignment(db: Session, assignment_id: int, end_date: date | None = None) -> VehicleAssignment:
    assignment = db.get(VehicleAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError(f"Assignment {assignment_id} was not found")

    assignment.is_active = False
    assignment.end_date = end_date or date.today()
    db.commit()
    db.refresh(assignment)
    return assignment


def list_assignments(
    db: Session,
    *,
    vehicle_id: int | None = None,
    driver_id: int | None = None,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[VehicleAssignment], int]:
    stmt = select(VehicleAssignment).options(
        selectinload(VehicleAssignment.vehicle),
        selectinload(VehicleAssignment.driver),
    )
    filters = []
    if vehicle_id is not None:
        filters.append(VehicleAssignment.vehicle_id == vehicle_id)
    if driver_id is not None:
        filters.append(VehicleAssignment.driver_id == driver_id)
    if active_only:
        filters.append(VehicleAssignment.is_active.is_(True))

    if filters:
        stmt = stmt.where(*filters)

    rows = list(
        db.scalars(
            stmt.order_by(VehicleAssignment.start_date.desc()).limit(limit).offset(offset)
        )
    )
    total = len(
        list(db.scalars(select(VehicleAssignment.id).where(*filters)))
        if filters
        else list(db.scalars(select(VehicleAssignment.id)))
    )
    return rows, total
