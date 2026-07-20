"""Plain HTTP handler — calls ``action.endpoint``. Wired up in phase 6.

Params shape:
    {"method": "POST", "headers": {...}, "body": {...}}
"""

from __future__ import annotations

from ..models import Action


async def handle(action: Action) -> dict:
    if not action.endpoint:
        return {"status": "error", "message": "no endpoint configured"}
    return {
        "status": "error",
        "message": f"fetch handler not implemented yet (phase 6) — target {action.endpoint}",
    }
