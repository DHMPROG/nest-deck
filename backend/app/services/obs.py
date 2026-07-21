"""OBS WebSocket handler (obsws-python).

Params shape:
    {"request": "SetCurrentProgramScene", "args": {"sceneName": "Camera"}}

`obsws-python` is synchronous and connects on construction, so the whole call
runs in a worker thread. A fresh client per request keeps things simple and
avoids holding a socket open against an OBS that may be closed most of the day;
the cost is one handshake per press, which is negligible on a LAN.
"""

from __future__ import annotations

import asyncio
import os
from urllib.parse import urlparse

from ..models import Action

OBS_URL = os.environ.get("OBS_URL", "ws://localhost:4455")
OBS_PASSWORD = os.environ.get("OBS_PASSWORD", "")
TIMEOUT_S = 3


def _endpoint(action: Action) -> tuple[str, int]:
    """Per-action override wins over the environment."""
    raw = action.endpoint or OBS_URL
    parsed = urlparse(raw if "//" in raw else f"ws://{raw}")
    return parsed.hostname or "localhost", parsed.port or 4455


def _call(host: str, port: int, request: str, args: dict) -> dict:
    import obsws_python as obsws

    client = obsws.ReqClient(
        host=host, port=port, password=OBS_PASSWORD, timeout=TIMEOUT_S
    )
    try:
        client.send(request, args or None)
    finally:
        try:
            client.disconnect()
        except Exception:  # noqa: BLE001 - never let cleanup mask the result
            pass
    return {"status": "ok", "message": f"OBS · {request}"}


async def handle(action: Action) -> dict:
    params = action.params or {}
    request = params.get("request")
    if not request:
        return {"status": "error", "message": "no OBS request configured"}

    host, port = _endpoint(action)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_call, host, port, request, params.get("args", {})),
            timeout=TIMEOUT_S + 2,
        )
    except asyncio.TimeoutError:
        return {"status": "error", "message": f"OBS · timeout ({host}:{port})"}
    except ImportError:
        return {"status": "error", "message": "obsws-python not installed"}
    except Exception as exc:  # noqa: BLE001 - offline OBS must degrade, not crash
        reason = str(exc) or type(exc).__name__
        return {"status": "error", "message": f"OBS · {reason}"}
