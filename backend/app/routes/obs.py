"""OBS discovery for the Editor: connection status, scenes, sources, audio inputs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..services import obs

router = APIRouter(tags=["obs"])


@router.get("/obs/state")
async def obs_state() -> dict[str, Any]:
    """Never fails: an unreachable OBS comes back as ``connected: false``."""
    return await obs.snapshot()
