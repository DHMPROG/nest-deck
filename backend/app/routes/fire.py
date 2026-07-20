"""Execute the action bound to a tile."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..database import get_session
from ..events import broadcast
from ..models import Action, Tile
from ..schemas import FireResult
from ..services.registry import get_handler

router = APIRouter(tags=["fire"])


@router.post("/fire/{tile_id}", response_model=FireResult)
async def fire_tile(tile_id: str, session: Session = Depends(get_session)):
    tile = session.get(Tile, tile_id)
    if tile is None:
        raise HTTPException(404, "tile not found")

    started = time.perf_counter()

    def _done(status: str, message: str) -> FireResult:
        duration_ms = int((time.perf_counter() - started) * 1000)
        broadcast("action_fired", tile_id=tile_id, status=status)
        return FireResult(status=status, message=message, duration_ms=duration_ms)

    if tile.action_id is None:
        return _done("error", "empty slot")

    action = session.get(Action, tile.action_id)
    if action is None:
        return _done("error", "action not found")

    action_type = action.type.value if hasattr(action.type, "value") else action.type
    handler = get_handler(action_type)
    if handler is None:
        return _done("error", f"no handler for type '{action_type}'")

    # A handler must never take the app down — degrade to an error tile instead.
    try:
        result = await handler(action)
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all
        return _done("error", f"{type(exc).__name__}: {exc}")

    status = result.get("status", "error")
    message = result.get("message", "")
    return _done(status, message)
