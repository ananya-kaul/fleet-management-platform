from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, FleetManager, Paging
from app.schemas.common import Page
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceDueItem,
    MaintenanceRead,
    MaintenanceUpdate,
)
from app.services import maintenance_service

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("", response_model=Page[MaintenanceRead])
def list_records(
    db: DbSession, _: CurrentUser, paging: Paging, vehicle_id: int | None = None
) -> Page[MaintenanceRead]:
    rows, total = maintenance_service.list_records(
        db, vehicle_id=vehicle_id, limit=paging.limit, offset=paging.offset
    )
    return Page(
        items=[MaintenanceRead.model_validate(row) for row in rows],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )


@router.post("", response_model=MaintenanceRead, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: MaintenanceCreate, db: DbSession, _: FleetManager
) -> MaintenanceRead:
    return MaintenanceRead.model_validate(maintenance_service.create_record(db, payload))


@router.get("/due", response_model=list[MaintenanceDueItem])
def vehicles_due(db: DbSession, _: CurrentUser) -> list[MaintenanceDueItem]:
    return maintenance_service.vehicles_due(db)


@router.get("/{record_id}", response_model=MaintenanceRead)
def get_record(record_id: int, db: DbSession, _: CurrentUser) -> MaintenanceRead:
    return MaintenanceRead.model_validate(maintenance_service.get_record(db, record_id))


@router.put("/{record_id}", response_model=MaintenanceRead)
def update_record(
    record_id: int, payload: MaintenanceUpdate, db: DbSession, _: FleetManager
) -> MaintenanceRead:
    return MaintenanceRead.model_validate(
        maintenance_service.update_record(db, record_id, payload)
    )
