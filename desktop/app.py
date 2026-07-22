"""Nest Deck desktop app.

Runs the embedded server in a background thread, reconnects to the last Nest
Hub, and opens a native window showing the Editor. The Deck itself lives on the
Hub as the cast page.
"""

from __future__ import annotations

import os
import threading
import time
import urllib.request

from server import ROOT, create_app  # noqa: F401 - create_app re-exported

PORT = int(os.environ.get("NESTDECK_PORT", "8770"))
HOST = "0.0.0.0"


def _serve() -> None:
    import uvicorn

    uvicorn.run(create_app(), host=HOST, port=PORT, log_level="warning")


def _wait_until_up(timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{PORT}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:  # noqa: BLE001 - server not up yet
            time.sleep(0.3)
    return False


def _autoconnect() -> None:
    """Reconnect to the remembered Hub, if any. Best-effort, off the UI thread."""
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from app.services.cast import cast_manager, lan_ip

    os.environ.setdefault("DECK_URL", f"http://{lan_ip()}:{PORT}/")
    cast_manager.autoconnect()


def main() -> None:
    import webview

    # Cast target = this machine on the LAN, on our port.
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from app.services.cast import lan_ip

    os.environ["DECK_URL"] = f"http://{lan_ip()}:{PORT}/"

    threading.Thread(target=_serve, daemon=True).start()
    if not _wait_until_up():
        raise RuntimeError("le serveur interne n'a pas démarré")

    # Reconnect to the Hub in the background so the window opens without waiting.
    threading.Thread(target=_autoconnect, daemon=True).start()

    webview.create_window(
        "Nest Deck",
        f"http://127.0.0.1:{PORT}/editor",
        width=1240,
        height=840,
        min_size=(1024, 700),
    )
    webview.start()


if __name__ == "__main__":
    main()
