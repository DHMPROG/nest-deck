"""Plain HTTP handler — calls `action.endpoint`.

Params shape:
    {"method": "POST", "headers": {...}, "body": {...}, "timeout": 5}

Uses the standard library rather than httpx: the spec asks to keep the
dependency count small, and this is a single request with no session reuse.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from ..models import Action

DEFAULT_TIMEOUT_S = 5


def _call(url: str, method: str, headers: dict, body: object, timeout: float) -> dict:
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers = {"content-type": "application/json", **headers}

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return {
            "status": "ok",
            "message": f"HTTP {response.status}",
        }


async def handle(action: Action) -> dict:
    if not action.endpoint:
        return {"status": "error", "message": "no endpoint configured"}

    params = action.params or {}
    method = str(params.get("method", "GET")).upper()
    headers = params.get("headers") or {}
    body = params.get("body")
    timeout = float(params.get("timeout", DEFAULT_TIMEOUT_S))

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_call, action.endpoint, method, headers, body, timeout),
            timeout=timeout + 2,
        )
    except asyncio.TimeoutError:
        return {"status": "error", "message": f"timeout after {timeout}s"}
    except urllib.error.HTTPError as exc:
        # The server answered, just not with a 2xx — report its status.
        return {"status": "error", "message": f"HTTP {exc.code}"}
    except urllib.error.URLError as exc:
        return {"status": "error", "message": f"unreachable: {exc.reason}"}
    except Exception as exc:  # noqa: BLE001 - handlers must never raise
        return {"status": "error", "message": str(exc) or type(exc).__name__}
