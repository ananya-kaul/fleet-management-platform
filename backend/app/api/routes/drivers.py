from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, FleetManager, Paging
from app.models import DriverStatus
from app.schemas.assignment import AssignmentRead
from app.schemas.common import Page
from app.schemas.driver import DriverCreate, DriverRead, DriverUpdate
from app.services import assignment_service, driver_service

router = APIRouter(prefix="/drivers", tags=["drivers"])


def _to_read(db, driver) -> DriverRead:
    assignment = driver_service.current_assignment(db, driver.id)
    return DriverRead(
        id=driver.id,
        name=driver.name,
        phone_number=driver.phone_number,
        license_number=driver.license_number,
        license_expiry=driver.license_expiry,
        status=driver.status,
        user_id=driver.user_id,
        assigned_vehicle_id=assignment.vehicle_id if assignment else None,
        assigned_vehicle_registration=(
            assignment.vehicle.registration_number if assignment else None
        ),
    )


@router.get("", response_model=Page[DriverRead])
def list_drivers(
    db: DbSession,
    _: FleetManager,
    paging: Paging,
    search: Annotated[str | None, Query(max_length=60)] = None,
    status_filter: Annotated[DriverStatus | None, Query(alias="status")] = None,
) -> Page[DriverRead]:
    rows, total = driver_service.list_drivers(
        db, search=search, status=status_filter, limit=paging.limit, offset=paging.offset
    )
    return Page(
        items=[_to_read(db, row) for row in rows],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )


@router.post("", response_model=DriverRead, status_code=status.HTTP_201_CREATED)
def create_driver(payload: DriverCreate, db: DbSession, _: FleetManager) -> DriverRead:
    return _to_read(db, driver_service.create_driver(db, payload))


@router.get("/me", response_model=DriverRead)
def my_profile(db: DbSession, user: CurrentUser) -> DriverRead:
    return _to_read(db, driver_service.get_driver_for_user(db, user))


@router.get("/{driver_id}", response_model=DriverRead)
def get_driver(driver_id: int, db: DbSession, _: FleetManager) -> DriverRead:
    return _to_read(db, driver_service.get_driver(db, driver_id))


@router.put("/{driver_id}", response_model=DriverRead)
def update_driver(
    driver_id: int, payload: DriverUpdate, db: DbSession, _: FleetManager
) -> DriverRead:
    return _to_read(db, driver_service.update_driver(db, driver_id, payload))


@router.post("/{driver_id}/status", response_model=DriverRead)
def set_status(
    driver_id: int, new_status: DriverStatus, db: DbSession, _: FleetManager
) -> DriverRead:
    return _to_read(db, driver_service.set_driver_status(db, driver_id, new_status))


@router.get("/{driver_id}/assignments", response_model=list[AssignmentRead])
def driver_history(driver_id: int, db: DbSession, _: FleetManager) -> list[AssignmentRead]:
    rows, _total = assignment_service.list_assignments(db, driver_id=driver_id, limit=200)
    return [AssignmentRead.model_validate(row) for row in rows]
