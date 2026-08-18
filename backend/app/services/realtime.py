"""In-process WebSocket fan-out for live vehicle positions.

Fleet managers subscribe to /ws/tracking and receive every location ping as it
is written. A multi-instance deployment would put Redis pub/sub behind this
class; the broadcast() signature would not change.
"""

import asyncio
import json
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info("Tracking socket connected (%d open)", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.info("Tracking socket closed (%d open)", len(self._connections))

    async def broadcast(self, event: str, payload: dict[str, Any]) -> None:
        message = json.dumps({"event": event, "data": payload}, default=str)
        async with self._lock:
            targets = list(self._connections)

        dead: list[WebSocket] = []
        for connection in targets:
            try:
                await connection.send_text(message)
            except Exception:  # noqa: BLE001 - a dropped client must not break the loop
                dead.append(connection)

        if dead:
            async with self._lock:
                for connection in dead:
                    self._connections.discard(connection)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


def broadcast_threadsafe(event: str, payload: dict[str, Any]) -> None:
    """Schedule a broadcast from sync request-handler code.

    Route handlers are sync (they use a blocking DB session), so they cannot
    await. When a running loop is present the coroutine is scheduled onto it;
    outside a loop (tests, scripts) the call is a no-op.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(manager.broadcast(event, payload))
