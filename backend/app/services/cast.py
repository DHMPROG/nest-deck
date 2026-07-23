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

# Docker sets CAST_SETTINGS=/data/cast.json; otherwise it sits next to deck.db
# (repo data dir from source, %APPDATA%/NestDeck when packaged).
from ..database import data_dir  # noqa: E402

_SETTINGS_PATH = Path(os.environ.get("CAST_SETTINGS", str(data_dir() / "cast.json")))


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
            # host/port let us reconnect (and re-discover) without mDNS, which
            # is unreliable on Windows: svchost and Bonjour already squat UDP
            # 5353 and unicast replies only reach one of the bound sockets.
            _SETTINGS_PATH.write_text(
                json.dumps(
                    {
                        "uuid": device["uuid"],
                        "name": device["name"],
                        "host": device.get("host"),
                        "port": device.get("port", 8009),
                        "model": device.get("model", ""),
                    }
                ),
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
    def _probe_lan(self, port: int = 8009, timeout: float = 0.4) -> list[str]:
        """Hosts on the local /24 with the Cast port open.

        mDNS discovery often finds nothing on Windows (UDP 5353 is contested by
        the system resolver and Bonjour, and Wi-Fi APs filter multicast), so we
        sweep the subnet with plain TCP connects instead — that needs nothing
        but an outbound socket.
        """
        from concurrent.futures import ThreadPoolExecutor

        ip = lan_ip()
        if ip.startswith("127."):
            return []
        base = ip.rsplit(".", 1)[0]
        candidates = [f"{base}.{i}" for i in range(1, 255) if f"{base}.{i}" != ip]

        def is_open(host: str) -> Optional[str]:
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return host
            except OSError:
                return None

        with ThreadPoolExecutor(max_workers=64) as pool:
            return [h for h in pool.map(is_open, candidates) if h]

    def scan(self, timeout: int = 6) -> list[dict]:
        import pychromecast

        # Opt-in diagnostics: NESTDECK_CAST_DEBUG=1 dumps zeroconf's view of the
        # scan (interfaces, packets) to cast_debug.log next to deck.db.
        debug_handler = None
        if os.environ.get("NESTDECK_CAST_DEBUG"):
            import logging

            debug_handler = logging.FileHandler(
                data_dir() / "cast_debug.log", encoding="utf-8"
            )
            debug_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
            for name in ("zeroconf", "pychromecast"):
                logger = logging.getLogger(name)
                logger.setLevel(logging.DEBUG)
                logger.addHandler(debug_handler)

        # Direct probing does the real work; mDNS is a bonus when it happens
        # to function. The remembered device is always probed, even if it sits
        # outside the swept /24.
        known_hosts = set(self._probe_lan())
        saved = self.remembered()
        if saved and saved.get("host"):
            known_hosts.add(saved["host"])

        chromecasts, browser = pychromecast.get_chromecasts(
            timeout=timeout, known_hosts=sorted(known_hosts) or None
        )
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

        if debug_handler is not None:
            import logging

            for name in ("zeroconf", "pychromecast"):
                logging.getLogger(name).removeHandler(debug_handler)
            debug_handler.close()

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
                # Last resort: the remembered device with a stored address can
                # be reached directly, no discovery involved.
                saved = self.remembered()
                if (
                    saved
                    and saved.get("host")
                    and (saved.get("uuid") == uuid or saved.get("name") == name)
                ):
                    device = {
                        "uuid": saved["uuid"],
                        "name": saved["name"],
                        "model": saved.get("model", ""),
                        "host": saved["host"],
                        "port": saved.get("port", 8009),
                    }
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
