"""Meeting shortcut handler (Meet / Zoom / Teams) — wired up in phase 6."""

from __future__ import annotations

from ..models import Action


async def handle(action: Action) -> dict:
    return {
        "status": "error",
        "message": "Meeting handler not implemented yet (phase 6)",
    }
