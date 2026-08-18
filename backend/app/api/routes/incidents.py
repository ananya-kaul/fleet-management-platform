from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, FleetManager, Paging
from app.models import IncidentStatus, UserRole
from app.schemas.common import Page
from app.schemas.incident import IncidentCreate, IncidentRead, IncidentUpdate
from app.services import driver_service, incident_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=Page[IncidentRead])
def list_incidents(
    db: DbSession,
    user: CurrentUser,
    paging: Paging,
    status_filter: IncidentStatus | None = None,
    vehicle_id: int | None = None,
) -> Page[IncidentRead]:
    driver_id = None
    if user.role == UserRole.DRIVER:
        driver_id = driver_service.get_driver_for_user(db, user).id

    rows, total = incident_service.list_incidents(
        db,
        status=status_filter,
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        limit=paging.limit,
        offset=paging.offset,
    )
    return Page(
        items=[IncidentRead.model_validate(row) for row in rows],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def report_incident(payload: IncidentCreate, db: DbSession, user: CurrentUser) -> IncidentRead:
    reporter = None
    if user.role == UserRole.DRIVER:
        reporter = driver_service.get_driver_for_user(db, user)
    return IncidentRead.model_validate(
        incident_service.report_incident(db, payload, reporter=reporter)
    )


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: DbSession, _: CurrentUser) -> IncidentRead:
    return IncidentRead.model_validate(incident_service.get_incident(db, incident_id))


@router.put("/{incident_id}", response_model=IncidentRead)
def update_incident(
    incident_id: int, payload: IncidentUpdate, db: DbSession, _: FleetManager
) -> IncidentRead:
    return IncidentRead.model_validate(
        incident_service.update_incident(db, incident_id, payload)
    )
