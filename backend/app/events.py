"""In-memory SSE broadcaster (pub/sub).

Mutating routes run in FastAPI's threadpool (they are sync ``def``), so
``broadcast()`` must be callable from a worker thread. We therefore capture the
main event loop at startup and hop back onto it with ``call_soon_threadsafe``.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

_main_loop: Optional[asyncio.AbstractEventLoop] = None
_QUEUE_LIMIT = 100


class Broadcaster:
    """Fan-out to every connected SSE client."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        # Bounded: a client that stopped reading (a Hub asleep on a half-open
        # socket) must not grow memory forever. It reloads every 9 minutes and
        # refetches everything then, so dropping its backlog loses nothing.
        queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_LIMIT)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    async def publish(self, event: dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass


broadcaster = Broadcaster()


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def broadcast(event_type: str, **payload: Any) -> None:
    """Publish an event. Never raises — a broken SSE client must not fail a write."""
    loop = _main_loop
    if loop is None or loop.is_closed():
        return

    event = {"type": event_type, "payload": payload}

    def _dispatch() -> None:
        loop.create_task(broadcaster.publish(event))

    try:
        loop.call_soon_threadsafe(_dispatch)
    except RuntimeError:
        # Loop shutting down; dropping the event is the correct behaviour.
        pass
