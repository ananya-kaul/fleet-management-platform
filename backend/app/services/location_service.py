"""GPS ingestion and lookup for live tracking."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import Location, Trip, TripStatus, Vehicle
from app.schemas.location import LocationCreate
from app.services import realtime


def record_location(db: Session, payload: LocationCreate, *, commit: bool = True) -> Location:
    vehicle = db.get(Vehicle, payload.vehicle_id)
    if vehicle is None:
        raise NotFoundError(f"Vehicle {payload.vehicle_id} was not found")

    if payload.trip_id is not None:
        trip = db.get(Trip, payload.trip_id)
        if trip is None:
            raise NotFoundError(f"Trip {payload.trip_id} was not found")
        if trip.vehicle_id != payload.vehicle_id:
            raise ConflictError(
                "Trip does not belong to the supplied vehicle", code="trip_vehicle_mismatch"
            )
        if trip.status not in (TripStatus.STARTED, TripStatus.IN_PROGRESS):
            raise ConflictError(
                f"Trip {trip.trip_code} is not active", code="trip_not_active"
            )

    location = Location(
        vehicle_id=payload.vehicle_id,
        trip_id=payload.trip_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        speed_kph=payload.speed_kph,
        heading=payload.heading,
        accuracy_m=payload.accuracy_m,
        recorded_at=payload.recorded_at or datetime.now(timezone.utc),
    )
    db.add(location)

    if commit:
        db.commit()
        db.refresh(location)
        _broadcast(location, vehicle)

    return location


def record_batch(db: Session, payloads: list[LocationCreate]) -> list[Location]:
    """Persist a batch of pings in one transaction (offline flush from mobile)."""
    saved = [record_location(db, payload, commit=False) for payload in payloads]
    db.commit()
    for location in saved:
        db.refresh(location)
        _broadcast(location, location.vehicle)
    return saved


def _broadcast(location: Location, vehicle: Vehicle) -> None:
    realtime.broadcast_threadsafe(
        "location.updated",
        {
            "vehicle_id": location.vehicle_id,
            "registration_number": vehicle.registration_number,
            "trip_id": location.trip_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "speed_kph": location.speed_kph,
            "heading": location.heading,
            "recorded_at": location.recorded_at,
        },
    )


def latest_for_vehicle(db: Session, vehicle_id: int) -> Location:
    location = db.scalar(
        select(Location)
        .where(Location.vehicle_id == vehicle_id)
        .order_by(Location.recorded_at.desc(), Location.id.desc())
    )
    if location is None:
        raise NotFoundError(f"No location has been recorded for vehicle {vehicle_id}")
    return location


def latest_positions(db: Session) -> list[Location]:
    """One most-recent ping per vehicle, for the fleet map."""
    vehicle_ids = list(db.scalars(select(Location.vehicle_id).distinct()))
    positions = []
    for vehicle_id in vehicle_ids:
        row = db.scalar(
            select(Location)
            .where(Location.vehicle_id == vehicle_id)
            .order_by(Location.recorded_at.desc(), Location.id.desc())
        )
        if row is not None:
            positions.append(row)
    return positions


def track_for_trip(db: Session, trip_id: int, limit: int = 1000) -> list[Location]:
    return list(
        db.scalars(
            select(Location)
            .where(Location.trip_id == trip_id)
            .order_by(Location.recorded_at.asc())
            .limit(limit)
        )
    )
