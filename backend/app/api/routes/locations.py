from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.api.deps import CurrentUser, DbSession, FleetManager
from app.schemas.location import LocationBatchCreate, LocationCreate, LocationRead
from app.services import location_service, realtime

router = APIRouter(tags=["tracking"])


@router.post("/locations", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def record_location(payload: LocationCreate, db: DbSession, _: CurrentUser) -> LocationRead:
    return LocationRead.model_validate(location_service.record_location(db, payload))


@router.post(
    "/locations/batch",
    response_model=list[LocationRead],
    status_code=status.HTTP_201_CREATED,
)
def record_batch(
    payload: LocationBatchCreate, db: DbSession, _: CurrentUser
) -> list[LocationRead]:
    saved = location_service.record_batch(db, payload.locations)
    return [LocationRead.model_validate(row) for row in saved]


@router.get("/locations/latest", response_model=list[LocationRead])
def latest_positions(db: DbSession, _: FleetManager) -> list[LocationRead]:
    return [
        LocationRead.model_validate(row) for row in location_service.latest_positions(db)
    ]


@router.websocket("/ws/tracking")
async def tracking_socket(websocket: WebSocket) -> None:
    """Live position feed for the fleet manager map.

    The handshake carries no auth because the browser WebSocket API cannot set
    headers; a production build would pass a short-lived ticket as a query
    parameter and validate it before accept().
    """
    await realtime.manager.connect(websocket)
    try:
        while True:
            # Keeps the connection open and surfaces client disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime.manager.disconnect(websocket)
    except Exception:  # noqa: BLE001
        await realtime.manager.disconnect(websocket)
