"""Fake handler used by the seeded catalog — always succeeds."""

from __future__ import annotations

import asyncio
import random

from ..models import Action


async def handle(action: Action) -> dict:
    await asyncio.sleep(random.uniform(0.2, 0.8))
    return {"status": "ok", "message": f"{action.label} · sent"}
