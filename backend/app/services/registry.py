"""Action type -> handler dispatch.

Every entry resolves to ``async def handle(action: Action) -> dict``. The only
exception is ``open``, which is a client-side concern: the Deck opens the URL
itself, the backend just acknowledges.
"""

from __future__ import annotations

from typing import Awaitable, Callable

from ..models import Action
from . import demo, fetch, launcher, meeting, obs, pc, spotify

Handler = Callable[[Action], Awaitable[dict]]


async def _open(action: Action) -> dict:
    """Open the URL in the default browser on the host PC (not on the Deck)."""
    import asyncio
    import webbrowser

    url = (action.endpoint or "").strip()
    if not url:
        return {"status": "error", "message": "aucune URL configurée"}

    try:
        opened = await asyncio.to_thread(webbrowser.open, url)
        if not opened:
            return {"status": "error", "message": "aucun navigateur disponible"}
        return {"status": "ok", "message": f"ouvert · {url}"}
    except Exception as exc:  # noqa: BLE001 - a handler must never raise
        return {"status": "error", "message": str(exc) or type(exc).__name__}


HANDLERS: dict[str, Handler] = {
    "demo": demo.handle,
    "fetch": fetch.handle,
    "obs": obs.handle,
    "spotify": spotify.handle,
    "pc": pc.handle,
    "meeting": meeting.handle,
    "launcher": launcher.handle,
    "open": _open,
}


def get_handler(action_type: str) -> Handler | None:
    return HANDLERS.get(action_type)
