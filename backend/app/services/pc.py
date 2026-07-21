"""Keyboard/mouse macro handler (pynput).

Params shape:
    {"combo": ["ctrl", "shift", "s"]}
    {"text": "hello"}
    {"launch": "steam"}            # delegated to the launcher handler

This only affects the machine the backend runs on. In the Docker setup that is
the container, which has no input device — see the README for the companion
daemon pattern.

`pynput` is imported lazily: it needs a display/input backend and raises on
import in a headless container, which must not take the whole app down.
"""

from __future__ import annotations

import asyncio

from ..models import Action

# Names accepted in a `combo`, mapped to pynput's Key members. Anything not
# listed is treated as a literal character ("s", "1", "/").
_MODIFIERS = {"ctrl", "ctrl_l", "ctrl_r", "alt", "alt_l", "alt_r", "alt_gr", "shift", "shift_l", "shift_r", "cmd", "cmd_l", "cmd_r"}

_ALIASES = {
    "control": "ctrl",
    "win": "cmd",
    "windows": "cmd",
    "super": "cmd",
    "meta": "cmd",
    "option": "alt",
    "return": "enter",
    "escape": "esc",
    "del": "delete",
    "pgup": "page_up",
    "pgdn": "page_down",
}


def _resolve(name: str):
    from pynput.keyboard import Key

    key = _ALIASES.get(name.lower(), name.lower())
    if len(key) == 1:
        return key
    if hasattr(Key, key):
        return getattr(Key, key)
    raise ValueError(f"unknown key: {name}")


def send_combo(combo: list[str]) -> None:
    """Press every key in order, then release in reverse. Blocking."""
    from pynput.keyboard import Controller

    keyboard = Controller()
    resolved = [_resolve(name) for name in combo]

    pressed = []
    try:
        for key in resolved:
            keyboard.press(key)
            pressed.append(key)
    finally:
        # Release even if a press failed, so no modifier stays stuck down.
        for key in reversed(pressed):
            try:
                keyboard.release(key)
            except Exception:  # noqa: BLE001
                pass


def _type_text(text: str) -> None:
    from pynput.keyboard import Controller

    Controller().type(text)


async def handle(action: Action) -> dict:
    params = action.params or {}

    if params.get("launch"):
        from . import launcher

        return await launcher.handle(action)

    combo = params.get("combo")
    text = params.get("text")

    if not combo and not text:
        return {"status": "error", "message": "no combo, text or launch configured"}

    try:
        if combo:
            if not isinstance(combo, list) or not all(isinstance(k, str) for k in combo):
                return {"status": "error", "message": "combo must be a list of strings"}
            await asyncio.to_thread(send_combo, combo)
            return {"status": "ok", "message": "+".join(combo)}

        await asyncio.to_thread(_type_text, str(text))
        return {"status": "ok", "message": "texte envoyé"}

    except ImportError:
        return {
            "status": "error",
            "message": "pynput unavailable (headless host?)",
        }
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:  # noqa: BLE001 - handlers must never raise
        return {"status": "error", "message": str(exc) or type(exc).__name__}
