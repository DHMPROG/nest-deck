"""Meeting shortcut handler.

Params shape:
    {"platform": "meet", "command": "mute"}
    {"platform": "zoom", "command": "leave", "os": "darwin"}

Resolves a platform + command pair to a key combo and hands it to the PC
handler. `os` defaults to the machine the backend runs on, since that is where
the keystroke lands.
"""

from __future__ import annotations

import asyncio
import sys

from ..models import Action
from . import pc

# platform -> command -> {os -> combo}. "*" applies to every OS.
SHORTCUTS: dict[str, dict[str, dict[str, list[str]]]] = {
    "meet": {
        "mute": {"darwin": ["cmd", "d"], "*": ["ctrl", "d"]},
        "camera": {"darwin": ["cmd", "e"], "*": ["ctrl", "e"]},
        "hand": {"darwin": ["cmd", "ctrl", "h"], "*": ["ctrl", "alt", "h"]},
        "chat": {"darwin": ["cmd", "ctrl", "c"], "*": ["ctrl", "alt", "c"]},
    },
    "zoom": {
        "mute": {"darwin": ["cmd", "shift", "a"], "*": ["alt", "a"]},
        "camera": {"darwin": ["cmd", "shift", "v"], "*": ["alt", "v"]},
        "share": {"darwin": ["cmd", "shift", "s"], "*": ["alt", "s"]},
        "hand": {"darwin": ["option", "y"], "*": ["alt", "y"]},
        "leave": {"darwin": ["cmd", "w"], "*": ["alt", "q"]},
        "chat": {"darwin": ["cmd", "shift", "h"], "*": ["alt", "h"]},
    },
    "teams": {
        "mute": {"darwin": ["cmd", "shift", "m"], "*": ["ctrl", "shift", "m"]},
        "camera": {"darwin": ["cmd", "shift", "o"], "*": ["ctrl", "shift", "o"]},
        "hand": {"darwin": ["cmd", "shift", "k"], "*": ["ctrl", "shift", "k"]},
        "leave": {"darwin": ["cmd", "shift", "h"], "*": ["ctrl", "shift", "h"]},
    },
}


def resolve(platform: str, command: str, os_name: str) -> list[str] | None:
    by_command = SHORTCUTS.get(platform.lower())
    if not by_command:
        return None
    by_os = by_command.get(command.lower())
    if not by_os:
        return None
    return by_os.get(os_name) or by_os.get("*")


async def handle(action: Action) -> dict:
    params = action.params or {}
    platform = params.get("platform")
    command = params.get("command")

    if not platform or not command:
        return {"status": "error", "message": "platform and command are required"}

    os_name = str(params.get("os") or sys.platform)
    combo = resolve(str(platform), str(command), os_name)

    if combo is None:
        known = ", ".join(sorted(SHORTCUTS))
        return {
            "status": "error",
            "message": f"unknown shortcut {platform}/{command} (known platforms: {known})",
        }

    try:
        await asyncio.to_thread(pc.send_combo, combo)
        return {"status": "ok", "message": f"{platform} · {'+'.join(combo)}"}
    except ImportError:
        return {"status": "error", "message": "pynput unavailable (headless host?)"}
    except Exception as exc:  # noqa: BLE001 - handlers must never raise
        return {"status": "error", "message": str(exc) or type(exc).__name__}
