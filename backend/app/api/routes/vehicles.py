from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, FleetManager, Paging
from app.models import VehicleStatus
from app.schemas.common import Page
from app.schemas.location import LocationRead
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate
from app.services import location_service, vehicle_service

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=Page[VehicleRead])
def list_vehicles(
    db: DbSession,
    _: CurrentUser,
    paging: Paging,
    search: Annotated[str | None, Query(max_length=60)] = None,
    status_filter: Annotated[VehicleStatus | None, Query(alias="status")] = None,
    is_active: bool | None = None,
) -> Page[VehicleRead]:
    rows, total = vehicle_service.list_vehicles(
        db,
        search=search,
        status=status_filter,
        is_active=is_active,
        limit=paging.limit,
        offset=paging.offset,
    )
    return Page(
        items=[VehicleRead.model_validate(row) for row in rows],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehicleCreate, db: DbSession, _: FleetManager) -> VehicleRead:
    return VehicleRead.model_validate(vehicle_service.create_vehicle(db, payload))


@router.get("/{vehicle_id}", response_model=VehicleRead)
def get_vehicle(vehicle_id: int, db: DbSession, _: CurrentUser) -> VehicleRead:
    return VehicleRead.model_validate(vehicle_service.get_vehicle(db, vehicle_id))


@router.put("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(
    vehicle_id: int, payload: VehicleUpdate, db: DbSession, _: FleetManager
) -> VehicleRead:
    return VehicleRead.model_validate(vehicle_service.update_vehicle(db, vehicle_id, payload))


@router.post("/{vehicle_id}/deactivate", response_model=VehicleRead)
def deactivate_vehicle(vehicle_id: int, db: DbSession, _: FleetManager) -> VehicleRead:
    return VehicleRead.model_validate(vehicle_service.deactivate_vehicle(db, vehicle_id))


@router.post("/{vehicle_id}/activate", response_model=VehicleRead)
def activate_vehicle(vehicle_id: int, db: DbSession, _: FleetManager) -> VehicleRead:
    return VehicleRead.model_validate(vehicle_service.activate_vehicle(db, vehicle_id))


@router.get("/{vehicle_id}/location", response_model=LocationRead)
def latest_location(vehicle_id: int, db: DbSession, _: CurrentUser) -> LocationRead:
    return LocationRead.model_validate(location_service.latest_for_vehicle(db, vehicle_id))
