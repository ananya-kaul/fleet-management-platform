"""Maintenance records and the "due for service" rule."""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import NotFoundError
from app.models import MaintenanceRecord, Vehicle, VehicleStatus
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceDueItem,
    MaintenanceUpdate,
)


def get_record(db: Session, record_id: int) -> MaintenanceRecord:
    record = db.get(MaintenanceRecord, record_id)
    if record is None:
        raise NotFoundError(f"Maintenance record {record_id} was not found")
    return record


def create_record(db: Session, payload: MaintenanceCreate) -> MaintenanceRecord:
    vehicle = db.get(Vehicle, payload.vehicle_id)
    if vehicle is None:
        raise NotFoundError(f"Vehicle {payload.vehicle_id} was not found")

    data = payload.model_dump()
    set_in_maintenance = data.pop("set_vehicle_in_maintenance")

    record = MaintenanceRecord(**data)
    db.add(record)

    if payload.odometer > float(vehicle.current_mileage):
        vehicle.current_mileage = payload.odometer
    if set_in_maintenance and vehicle.status == VehicleStatus.AVAILABLE:
        vehicle.status = VehicleStatus.IN_MAINTENANCE

    db.commit()
    db.refresh(record)
    return record


def update_record(db: Session, record_id: int, payload: MaintenanceUpdate) -> MaintenanceRecord:
    record = get_record(db, record_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


def list_records(
    db: Session,
    *,
    vehicle_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[MaintenanceRecord], int]:
    stmt = select(MaintenanceRecord).options(selectinload(MaintenanceRecord.vehicle))
    count_stmt = select(func.count()).select_from(MaintenanceRecord)

    if vehicle_id is not None:
        stmt = stmt.where(MaintenanceRecord.vehicle_id == vehicle_id)
        count_stmt = count_stmt.where(MaintenanceRecord.vehicle_id == vehicle_id)

    total = db.scalar(count_stmt) or 0
    rows = list(
        db.scalars(
            stmt.order_by(MaintenanceRecord.service_date.desc()).limit(limit).offset(offset)
        )
    )
    return rows, total


def vehicles_due(db: Session, *, window_days: int | None = None) -> list[MaintenanceDueItem]:
    """A vehicle is due when its latest record's next service date or mileage is reached.

    Date-based and mileage-based triggers are reported independently so a
    manager can see which one fired.
    """
    horizon_days = window_days if window_days is not None else settings.maintenance_due_window_days
    cutoff = date.today() + timedelta(days=horizon_days)
    due: list[MaintenanceDueItem] = []

    vehicles = list(db.scalars(select(Vehicle).where(Vehicle.is_active.is_(True))))
    for vehicle in vehicles:
        latest = db.scalar(
            select(MaintenanceRecord)
            .where(MaintenanceRecord.vehicle_id == vehicle.id)
            .order_by(MaintenanceRecord.service_date.desc(), MaintenanceRecord.id.desc())
        )
        if latest is None:
            continue

        if latest.next_service_date is not None and latest.next_service_date <= cutoff:
            due.append(
                MaintenanceDueItem(
                    vehicle_id=vehicle.id,
                    registration_number=vehicle.registration_number,
                    reason=f"{latest.maintenance_type} due by {latest.next_service_date}",
                    due_date=latest.next_service_date,
                )
            )
            continue

        if (
            latest.next_service_mileage is not None
            and float(vehicle.current_mileage) >= float(latest.next_service_mileage)
        ):
            due.append(
                MaintenanceDueItem(
                    vehicle_id=vehicle.id,
                    registration_number=vehicle.registration_number,
                    reason=(
                        f"Odometer {float(vehicle.current_mileage):.0f} km has passed the "
                        f"{float(latest.next_service_mileage):.0f} km service point"
                    ),
                    due_mileage=float(latest.next_service_mileage),
                )
            )

    return due
