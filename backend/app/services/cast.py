"""Chromecast control for the desktop app.

Discovers Google Cast devices on the LAN, casts the Deck URL to one via the
DashCast receiver (the same mechanism `catt cast_site` uses), remembers the
last device, and reconnects to it on startup.

pychromecast spins its own background threads, so every public method here is
synchronous and meant to be called from FastAPI's threadpool, never awaited on
the event loop.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any, Optional

# The receiver app that shows an arbitrary web page; when the Hub falls back to
# its photo frame this becomes "Backdrop".
_DASHCAST_APP_ID = "84912283"
_IDLE_APPS = {"Backdrop", "", None}

# Docker sets CAST_SETTINGS=/data/cast.json; natively it lands in the repo's
# data dir, next to deck.db.
_DEFAULT_SETTINGS = Path(__file__).resolve().parents[3] / "data" / "cast.json"
_SETTINGS_PATH = Path(os.environ.get("CAST_SETTINGS", str(_DEFAULT_SETTINGS)))


def lan_ip() -> str:
    """The address other devices on the LAN can reach this machine at."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No packet is actually sent; this just picks the outbound interface.
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class CastManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cast: Any = None  # the connected pychromecast.Chromecast
        self._dash: Any = None  # its DashCastController
        self._device: Optional[dict] = None  # currently targeted device info
        self._devices: dict[str, dict] = {}  # last scan, uuid -> info

    # -- deck URL -------------------------------------------------------------
    def deck_url(self) -> str:
        """The page to cast. Set explicitly by the desktop launcher; otherwise
        computed from the LAN IP and the served port."""
        explicit = os.environ.get("DECK_URL")
        if explicit:
            return explicit
        port = os.environ.get("DECK_PORT", "8080")
        return f"http://{lan_ip()}:{port}/"

    # -- persistence ----------------------------------------------------------
    def _remember(self, device: dict) -> None:
        try:
            _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            _SETTINGS_PATH.write_text(
                json.dumps({"uuid": device["uuid"], "name": device["name"]}),
                encoding="utf-8",
            )
        except OSError:
            pass  # a non-writable settings file must not break casting

    def remembered(self) -> Optional[dict]:
        try:
            return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def forget(self) -> None:
        try:
            _SETTINGS_PATH.unlink()
        except OSError:
            pass

    # -- discovery ------------------------------------------------------------
    def scan(self, timeout: int = 6) -> list[dict]:
        import pychromecast

        chromecasts, browser = pychromecast.get_chromecasts(timeout=timeout)
        found: dict[str, dict] = {}
        for cc in chromecasts:
            info = cc.cast_info
            found[str(info.uuid)] = {
                "uuid": str(info.uuid),
                "name": info.friendly_name,
                "model": info.model_name,
                "host": info.host,
                "port": info.port,
            }
        try:
            pychromecast.discovery.stop_discovery(browser)
        except Exception:  # noqa: BLE001
            pass

        with self._lock:
            self._devices = found
        return sorted(found.values(), key=lambda d: d["name"].lower())

    # -- connect / cast -------------------------------------------------------
    def connect(self, *, uuid: Optional[str] = None, name: Optional[str] = None) -> dict:
        import uuid as uuidlib

        import pychromecast
        from pychromecast.controllers.dashcast import DashCastController

        with self._lock:
            device = self._find(uuid, name)
            if device is None:
                # The cached scan may be stale; try once more before giving up.
                self.scan()
                device = self._find(uuid, name)
            if device is None:
                raise LookupError("appareil introuvable sur le réseau")

            self._teardown()

            # Connect straight to the known host — no rescan needed, which also
            # makes reconnecting to a remembered device fast on startup.
            host_tuple = (
                device["host"],
                int(device["port"]),
                uuidlib.UUID(device["uuid"]),
                device["model"],
                device["name"],
            )
            cast = pychromecast.get_chromecast_from_host(host_tuple, timeout=15)
            cast.wait(timeout=15)

            dash = DashCastController()
            cast.register_handler(dash)
            time.sleep(0.5)
            dash.load_url(self.deck_url(), force=True)

            self._cast = cast
            self._dash = dash
            self._device = device
            self._remember(device)

        return self.status()

    def recast(self) -> dict:
        """Reload the Deck URL on the already-connected device."""
        with self._lock:
            if self._cast is None or self._dash is None:
                raise RuntimeError("aucun appareil connecté")
            self._dash.load_url(self.deck_url(), force=True)
        return self.status()

    def disconnect(self) -> None:
        with self._lock:
            self._teardown()
            self._device = None

    def autoconnect(self) -> Optional[dict]:
        """Reconnect to the remembered device, if any. Best-effort."""
        saved = self.remembered()
        if not saved:
            return None
        try:
            return self.connect(uuid=saved.get("uuid"), name=saved.get("name"))
        except Exception:  # noqa: BLE001 - a missing device must not crash boot
            return None

    # -- status ---------------------------------------------------------------
    def status(self) -> dict:
        with self._lock:
            if self._cast is None or self._device is None:
                return {"connected": False, "device": None, "casting": False}

            app = None
            try:
                app = self._cast.status.display_name if self._cast.status else None
            except Exception:  # noqa: BLE001
                app = None

            return {
                "connected": True,
                "device": self._device,
                "casting": app not in _IDLE_APPS,
                "current_app": app,
                "deck_url": self.deck_url(),
            }

    # -- internals ------------------------------------------------------------
    def _find(self, uuid: Optional[str], name: Optional[str]) -> Optional[dict]:
        if uuid and uuid in self._devices:
            return self._devices[uuid]
        if name:
            for device in self._devices.values():
                if device["name"] == name:
                    return device
        return None

    def _teardown(self) -> None:
        if self._cast is not None:
            try:
                self._cast.disconnect(timeout=5)
            except Exception:  # noqa: BLE001
                pass
        self._cast = None
        self._dash = None


cast_manager = CastManager()
