"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import events as events_module
from .database import DATABASE_URL, init_db
from .routes import actions, categories, events, fire, pages, profiles, tiles
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

# Single-user LAN app — no auth, permissive CORS by design (see spec non-goals).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (profiles, pages, tiles, actions, categories, fire, events):
    app.include_router(module.router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "database": DATABASE_URL}
