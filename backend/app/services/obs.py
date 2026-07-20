"""OBS WebSocket handler — wired up in phase 6 with obsws-python.

Params shape:
    {"request": "SetCurrentProgramScene", "args": {"sceneName": "Camera"}}
"""

from __future__ import annotations

import os

from ..models import Action

OBS_URL = os.environ.get("OBS_URL", "ws://localhost:4455")
OBS_PASSWORD = os.environ.get("OBS_PASSWORD", "")


async def handle(action: Action) -> dict:
    return {
        "status": "error",
        "message": f"OBS handler not implemented yet (phase 6) — target {OBS_URL}",
    }
