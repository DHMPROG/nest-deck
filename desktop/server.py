"""The embedded web server for the desktop app.

Serves the backend API and the built frontend on a single port, so the Deck
(cast to the Hub) and the Editor (shown in the desktop window) come from the
same origin — the client keeps using a relative /api with no proxy.

Kept separate from the window (``app.py``) so this part can be started and
tested on its own.
"""

from __future__ import annotations

import os
import sys

from paths import ROOT, resource

# Make the backend package importable without installing it.
sys.path.insert(0, str(ROOT / "backend"))

FRONTEND_BUILD = resource("frontend/build")


def create_app():
    """The FastAPI backend with the built frontend mounted under it."""
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from starlette.staticfiles import StaticFiles

    from app.main import app  # noqa: PLC0415 - imported after sys.path tweak

    if not FRONTEND_BUILD.exists():
        raise FileNotFoundError(
            f"frontend build introuvable ({FRONTEND_BUILD}). "
            "Lance `npm run build` dans frontend/ d'abord."
        )

    class SPAStaticFiles(StaticFiles):
        """Serve static files, falling back to index.html for client routes
        like /editor. StaticFiles *raises* 404 rather than returning it, so the
        fallback has to be in an except block."""

        async def get_response(self, path, scope):
            try:
                return await super().get_response(path, scope)
            except StarletteHTTPException as exc:
                if exc.status_code == 404:
                    return await super().get_response("index.html", scope)
                raise

    # Mounted last, so the already-registered /api routes match first and
    # everything else falls through to the static files.
    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_BUILD), html=True))
    return app


def run(host: str = "0.0.0.0", port: int = 8770) -> None:
    import uvicorn

    # The Deck cast to the Hub must point back at this machine on the LAN.
    from app.services.cast import lan_ip  # noqa: PLC0415

    os.environ.setdefault("DECK_URL", f"http://{lan_ip()}:{port}/")
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run()
