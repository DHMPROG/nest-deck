"""SSE stream consumed by the Deck and the Editor."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from ..events import broadcaster

router = APIRouter(tags=["events"])

# Keeps proxies and the Nest Hub's Chromium from dropping an idle stream.
_KEEPALIVE_SECONDS = 15


@router.get("/events")
async def stream_events(request: Request):
    queue = broadcaster.subscribe()

    async def generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=_KEEPALIVE_SECONDS
                    )
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                yield {
                    "event": event["type"],
                    "data": json.dumps(event["payload"]),
                }
        finally:
            broadcaster.unsubscribe(queue)

    return EventSourceResponse(generator())
