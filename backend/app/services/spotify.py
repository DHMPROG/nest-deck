"""Spotify Web API handler (spotipy).

Params shape:
    {"command": "play"}          # play | pause | toggle | next | previous
    {"command": "volume", "value": 40}
    {"command": "transfer", "device": "Bureau"}

Requires SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET and SPOTIPY_REDIRECT_URI, and
a token cached by the one-off OAuth consent documented in the README. Without
them the handler degrades to an error tile rather than blocking on a browser
prompt that nobody would see on a kiosk.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from ..models import Action

from ..database import data_dir

SCOPE = "user-modify-playback-state user-read-playback-state"
CACHE_PATH = os.environ.get("SPOTIFY_CACHE", str(data_dir() / ".spotify-cache"))
TIMEOUT_S = 6


def _client():
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    auth = SpotifyOAuth(
        scope=SCOPE,
        cache_path=CACHE_PATH,
        # Never pop a browser: the deck has no way to complete a consent flow.
        open_browser=False,
    )
    token = auth.cache_handler.get_cached_token()
    if not token:
        raise RuntimeError("not authorised — run the OAuth setup (see README)")

    return spotipy.Spotify(auth_manager=auth, requests_timeout=TIMEOUT_S)


def _run(command: str, params: dict) -> dict:
    client = _client()

    if command in {"play", "resume"}:
        client.start_playback()
        return {"status": "ok", "message": "Spotify · lecture"}

    if command == "pause":
        client.pause_playback()
        return {"status": "ok", "message": "Spotify · pause"}

    if command == "toggle":
        state = client.current_playback()
        if state and state.get("is_playing"):
            client.pause_playback()
            return {"status": "ok", "message": "Spotify · pause"}
        client.start_playback()
        return {"status": "ok", "message": "Spotify · lecture"}

    if command == "next":
        client.next_track()
        return {"status": "ok", "message": "Spotify · piste suivante"}

    if command in {"previous", "prev"}:
        client.previous_track()
        return {"status": "ok", "message": "Spotify · piste précédente"}

    if command == "volume":
        value = int(params.get("value", 50))
        client.volume(max(0, min(100, value)))
        return {"status": "ok", "message": f"Spotify · volume {value}%"}

    if command == "shuffle":
        state = bool(params.get("value", True))
        client.shuffle(state)
        return {"status": "ok", "message": f"Spotify · shuffle {'on' if state else 'off'}"}

    return {"status": "error", "message": f"unknown Spotify command: {command}"}


async def handle(action: Action) -> dict:
    params = action.params or {}
    command = str(params.get("command", "")).lower()
    if not command:
        return {"status": "error", "message": "no Spotify command configured"}

    if not os.environ.get("SPOTIPY_CLIENT_ID"):
        return {"status": "error", "message": "Spotify non configuré (voir README)"}

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_run, command, params), timeout=TIMEOUT_S + 3
        )
    except asyncio.TimeoutError:
        return {"status": "error", "message": "Spotify · timeout"}
    except ImportError:
        return {"status": "error", "message": "spotipy not installed"}
    except Exception as exc:  # noqa: BLE001 - expired tokens must not crash
        reason = str(exc) or type(exc).__name__
        # Spotify returns 404 when no device is active — a common, fixable case.
        if "NO_ACTIVE_DEVICE" in reason or "404" in reason:
            reason = "aucun appareil actif"
        return {"status": "error", "message": f"Spotify · {reason}"}


def cache_dir_exists() -> bool:
    """Used by the README setup check."""
    return Path(CACHE_PATH).parent.exists()
