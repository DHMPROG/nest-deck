"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import events as events_module
from .database import DATABASE_URL, init_db
from .guard import LocalOnlyGuard
from .routes import (
    actions,
    cast,
    categories,
    events,
    fire,
    obs,
    pages,
    profiles,
    settings,
    system,
    tiles,
)
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()
    # Sync routes run in the threadpool; the broadcaster needs this loop to
    # dispatch SSE events from those threads.
    events_module.set_main_loop(asyncio.get_running_loop())
    yield


app = FastAPI(
    title="Nest Deck",
    description="FastAPI relay for the Nest Hub Max stream deck",
    version="0.1.0",
    lifespan=lifespan,
)

# Single-user LAN app with no auth — so the one thing to keep out is a web page
# in the user's own browser. Launcher tiles run shell commands, so a site that
# could reach this API could run anything on the PC.
app.add_middleware(LocalOnlyGuard)

for module in (
    profiles,
    pages,
    tiles,
    actions,
    categories,
    fire,
    events,
    system,
    cast,
    settings,
    obs,
):
    app.include_router(module.router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "database": DATABASE_URL}
