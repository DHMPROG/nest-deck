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
    """Client-side concern: the Deck opens the URL, the backend just acks."""
    return {"status": "ok", "message": "open in deck client"}


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
