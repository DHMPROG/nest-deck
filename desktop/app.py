"""Nest Deck desktop app.

Opens a native window on the splash, boots the embedded server and reconnects
to the last Nest Hub in the background (updating the splash status), then swaps
the window over to the Editor. The Deck itself lives on the Hub as the cast page.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import urllib.request

from paths import ROOT, resource
from server import create_app
from splash import splash_html

PORT = int(os.environ.get("NESTDECK_PORT", "8770"))
HOST = "0.0.0.0"

sys.path.insert(0, str(ROOT / "backend"))


def _serve() -> None:
    import uvicorn

    uvicorn.run(create_app(), host=HOST, port=PORT, log_level="warning")


def _wait_until_up(timeout: float = 25.0) -> bool:
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


def _set_status(window, text: str) -> None:
    """Update the splash status line, ignoring races during navigation."""
    try:
        window.evaluate_js(f"setStatus({text!r})")
    except Exception:  # noqa: BLE001
        pass


def _boot(window) -> None:
    """Runs after the GUI loop starts: wait for the server, reconnect the Hub,
    then swap the splash for the Editor."""
    from app.services.cast import cast_manager

    if not _wait_until_up():
        _set_status(window, "Le serveur n'a pas démarré")
        return

    # Reconnect to the remembered Hub, surfacing it on the splash.
    saved = cast_manager.remembered()
    if saved:
        _set_status(window, f"Connexion à « {saved.get('name', 'l’écran')} »…")
        cast_manager.autoconnect()

    _set_status(window, "Prêt")
    window.load_url(f"http://127.0.0.1:{PORT}/editor")


def main() -> None:
    import webview

    from app.services.cast import lan_ip

    # The Deck cast to the Hub points back at this machine on our port.
    os.environ["DECK_URL"] = f"http://{lan_ip()}:{PORT}/"

    # Start the server now so it boots in parallel with the window — the splash
    # covers the gap. Doing it here (not in _boot) means it comes up even if the
    # GUI is slow to initialise.
    threading.Thread(target=_serve, daemon=True).start()

    window = webview.create_window(
        "Nest Deck",
        html=splash_html(),
        width=1240,
        height=840,
        min_size=(1024, 700),
        background_color="#FAF9F7",
    )
    # `_boot` runs on a worker once the GUI is ready; webview.start blocks here.
    # private_mode=False keeps the webview's localStorage (e.g. the dark-mode
    # choice) across launches.
    webview.start(
        _boot,
        window,
        private_mode=False,
        icon=str(resource("desktop/assets/NestDeck.ico")),
    )


if __name__ == "__main__":
    main()
