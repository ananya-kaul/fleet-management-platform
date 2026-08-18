from datetime import date

from fastapi import APIRouter, status

from app.api.deps import DbSession, FleetManager, Paging
from app.schemas.assignment import AssignmentCreate, AssignmentRead
from app.schemas.common import Page
from app.services import assignment_service

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("", response_model=Page[AssignmentRead])
def list_assignments(
    db: DbSession,
    _: FleetManager,
    paging: Paging,
    vehicle_id: int | None = None,
    driver_id: int | None = None,
    active_only: bool = False,
) -> Page[AssignmentRead]:
    rows, total = assignment_service.list_assignments(
        db,
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        active_only=active_only,
        limit=paging.limit,
        offset=paging.offset,
    )
    return Page(
        items=[AssignmentRead.model_validate(row) for row in rows],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate, db: DbSession, _: FleetManager
) -> AssignmentRead:
    return AssignmentRead.model_validate(assignment_service.create_assignment(db, payload))


@router.post("/{assignment_id}/end", response_model=AssignmentRead)
def end_assignment(
    assignment_id: int, db: DbSession, _: FleetManager, end_date: date | None = None
) -> AssignmentRead:
    return AssignmentRead.model_validate(
        assignment_service.end_assignment(db, assignment_id, end_date)
    )
