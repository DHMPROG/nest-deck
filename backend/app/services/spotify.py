"""Spotify Web API handler — wired up in phase 6 with spotipy (OAuth)."""

from __future__ import annotations

from ..models import Action


async def handle(action: Action) -> dict:
    return {
        "status": "error",
        "message": "Spotify handler not implemented yet (phase 6)",
    }
