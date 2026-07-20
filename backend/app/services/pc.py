"""Keyboard/mouse macro handler — wired up in phase 6 with pynput.

Params shape:
    {"combo": ["ctrl", "shift", "s"]}   or   {"launch": "steam"}

Only works when the backend runs on the machine being controlled; see README
for the companion-daemon setup.
"""

from __future__ import annotations

from ..models import Action


async def handle(action: Action) -> dict:
    return {
        "status": "error",
        "message": "PC handler not implemented yet (phase 6)",
    }
