"""Keep other web sites out of the API.

The Deck and the Editor are served from the same origin as the API, so the
backend needs no CORS at all. Two checks remain:

- ``Origin``: a browser sends it on cross-site requests. If present, it must
  name the same host as the request, or the call came from another site.
- ``Host``: a DNS-rebinding attack points a domain the attacker owns at this
  machine, which makes the request look same-origin. IP literals, localhost
  and mDNS ``.local`` names cannot be rebound from outside, so only those pass.
  ``NESTDECK_ALLOWED_HOSTS`` (comma-separated) adds any other name you use.

Pure ASGI rather than ``BaseHTTPMiddleware``, which buffers the SSE stream.
"""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlsplit

_EXTRA_HOSTS = {
    h.strip().lower()
    for h in os.environ.get("NESTDECK_ALLOWED_HOSTS", "").split(",")
    if h.strip()
}


def _split(netloc: str, default_port: int) -> tuple[str, int] | None:
    try:
        parts = urlsplit(f"//{netloc}")
        return (parts.hostname or "").lower(), parts.port or default_port
    except ValueError:
        return None


def _trusted_host(hostname: str) -> bool:
    if hostname == "localhost" or hostname.endswith(".local") or hostname in _EXTRA_HOSTS:
        return True
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def request_allowed(host: str | None, origin: str | None) -> bool:
    target = _split(host or "", 80)
    if target is None or not _trusted_host(target[0]):
        return False
    if origin is None:
        return True  # same-origin GET, curl, the desktop app's health check
    parts = urlsplit(origin)
    if parts.scheme not in ("http", "https"):
        return False  # includes the literal "null" of sandboxed frames / file://
    source = _split(parts.netloc, 443 if parts.scheme == "https" else 80)
    return source == target


class LocalOnlyGuard:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}
            if not request_allowed(headers.get("host"), headers.get("origin")):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [(b"content-type", b"text/plain")],
                    }
                )
                await send({"type": "http.response.body", "body": b"forbidden origin"})
                return
        await self.app(scope, receive, send)
