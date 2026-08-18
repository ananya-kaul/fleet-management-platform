"""Driver-reported vehicle issues and manager triage."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError
from app.models import (
    Driver,
    Incident,
    IncidentStatus,
    NotificationCategory,
    Trip,
    Vehicle,
)
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services import notification_service


def get_incident(db: Session, incident_id: int) -> Incident:
    incident = db.scalar(
        select(Incident)
        .options(selectinload(Incident.vehicle), selectinload(Incident.reported_by))
        .where(Incident.id == incident_id)
    )
    if incident is None:
        raise NotFoundError(f"Incident {incident_id} was not found")
    return incident


def report_incident(
    db: Session, payload: IncidentCreate, *, reporter: Driver | None = None
) -> Incident:
    vehicle = db.get(Vehicle, payload.vehicle_id)
    if vehicle is None:
        raise NotFoundError(f"Vehicle {payload.vehicle_id} was not found")

    if payload.trip_id is not None:
        trip = db.get(Trip, payload.trip_id)
        if trip is None:
            raise NotFoundError(f"Trip {payload.trip_id} was not found")
        if trip.vehicle_id != payload.vehicle_id:
            raise ConflictError(
                "Trip does not belong to the supplied vehicle",
                code="trip_vehicle_mismatch",
            )

    incident = Incident(
        vehicle_id=payload.vehicle_id,
        trip_id=payload.trip_id,
        reported_by_driver_id=reporter.id if reporter else None,
        title=payload.title.strip(),
        description=payload.description,
        severity=payload.severity,
        status=IncidentStatus.OPEN,
        reported_at=payload.reported_at or datetime.now(timezone.utc),
    )
    db.add(incident)
    db.flush()

    notification_service.notify_fleet_managers(
        db,
        category=NotificationCategory.INCIDENT_REPORTED,
        title=f"{payload.severity} issue on {vehicle.registration_number}",
        body=incident.title,
        reference=f"incident:{incident.id}",
        commit=False,
    )

    db.commit()
    db.refresh(incident)
    return incident


def update_incident(db: Session, incident_id: int, payload: IncidentUpdate) -> Incident:
    incident = get_incident(db, incident_id)
    changes = payload.model_dump(exclude_unset=True)

    new_status = changes.get("status")
    if new_status is not None:
        if incident.status == IncidentStatus.RESOLVED and new_status != IncidentStatus.RESOLVED:
            raise ConflictError(
                "A resolved incident cannot be reopened", code="incident_resolved"
            )
        if new_status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.now(timezone.utc)

    for field, value in changes.items():
        setattr(incident, field, value)

    db.commit()
    db.refresh(incident)
    return incident


def list_incidents(
    db: Session,
    *,
    status: IncidentStatus | None = None,
    vehicle_id: int | None = None,
    driver_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Incident], int]:
    stmt = select(Incident).options(
        selectinload(Incident.vehicle), selectinload(Incident.reported_by)
    )
    count_stmt = select(func.count()).select_from(Incident)

    filters = []
    if status is not None:
        filters.append(Incident.status == status)
    if vehicle_id is not None:
        filters.append(Incident.vehicle_id == vehicle_id)
    if driver_id is not None:
        filters.append(Incident.reported_by_driver_id == driver_id)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = db.scalar(count_stmt) or 0
    rows = list(
        db.scalars(stmt.order_by(Incident.reported_at.desc()).limit(limit).offset(offset))
    )
    return rows, total
