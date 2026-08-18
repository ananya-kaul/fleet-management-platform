from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, FleetManager, Paging
from app.core.errors import PermissionDeniedError
from app.models import TripStatus, UserRole
from app.schemas.common import Page
from app.schemas.location import LocationRead
from app.schemas.trip import (
    TripCompleteRequest,
    TripCreate,
    TripRead,
    TripStartRequest,
    TripStatusUpdate,
    TripUpdate,
)
from app.services import driver_service, location_service, trip_service

router = APIRouter(prefix="/trips", tags=["trips"])


def _assert_can_act_on(db, user, trip) -> None:
    """Managers act on any trip; a driver may only act on their own."""
    if user.role == UserRole.FLEET_MANAGER:
        return
    driver = driver_service.get_driver_for_user(db, user)
    if trip.driver_id != driver.id:
        raise PermissionDeniedError("This trip is not assigned to you")


@router.get("", response_model=Page[TripRead])
def list_trips(
    db: DbSession,
    user: CurrentUser,
    paging: Paging,
    status_filter: TripStatus | None = None,
    vehicle_id: int | None = None,
    driver_id: int | None = None,
    active_only: bool = False,
) -> Page[TripRead]:
    # Drivers only ever see their own trips, whatever they ask for.
    if user.role == UserRole.DRIVER:
        driver_id = driver_service.get_driver_for_user(db, user).id

    rows, total = trip_service.list_trips(
        db,
        status=status_filter,
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        active_only=active_only,
        limit=paging.limit,
        offset=paging.offset,
    )
    return Page(
        items=[TripRead.model_validate(row) for row in rows],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )


@router.post("", response_model=TripRead, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, db: DbSession, _: FleetManager) -> TripRead:
    return TripRead.model_validate(trip_service.create_trip(db, payload))


@router.get("/{trip_id}", response_model=TripRead)
def get_trip(trip_id: int, db: DbSession, user: CurrentUser) -> TripRead:
    trip = trip_service.get_trip(db, trip_id)
    _assert_can_act_on(db, user, trip)
    return TripRead.model_validate(trip)


@router.put("/{trip_id}", response_model=TripRead)
def update_trip(
    trip_id: int, payload: TripUpdate, db: DbSession, _: FleetManager
) -> TripRead:
    return TripRead.model_validate(trip_service.update_trip(db, trip_id, payload))


@router.post("/{trip_id}/start", response_model=TripRead)
def start_trip(
    trip_id: int, payload: TripStartRequest, db: DbSession, user: CurrentUser
) -> TripRead:
    trip = trip_service.get_trip(db, trip_id)
    _assert_can_act_on(db, user, trip)
    return TripRead.model_validate(trip_service.start_trip(db, trip_id, payload))


@router.post("/{trip_id}/complete", response_model=TripRead)
def complete_trip(
    trip_id: int, payload: TripCompleteRequest, db: DbSession, user: CurrentUser
) -> TripRead:
    trip = trip_service.get_trip(db, trip_id)
    _assert_can_act_on(db, user, trip)
    return TripRead.model_validate(trip_service.complete_trip(db, trip_id, payload))


@router.post("/{trip_id}/status", response_model=TripRead)
def change_status(
    trip_id: int, payload: TripStatusUpdate, db: DbSession, user: CurrentUser
) -> TripRead:
    trip = trip_service.get_trip(db, trip_id)
    _assert_can_act_on(db, user, trip)
    return TripRead.model_validate(
        trip_service.change_status(db, trip_id, payload.status, payload.reason)
    )


@router.get("/{trip_id}/track", response_model=list[LocationRead])
def trip_track(trip_id: int, db: DbSession, user: CurrentUser) -> list[LocationRead]:
    trip = trip_service.get_trip(db, trip_id)
    _assert_can_act_on(db, user, trip)
    return [
        LocationRead.model_validate(row) for row in location_service.track_for_trip(db, trip_id)
    ]
