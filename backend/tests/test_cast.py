"""Casting: a slow connect must not freeze the status the Editor polls."""

from __future__ import annotations

import threading
import time


class _FakeCast:
    status = None

    def wait(self, timeout=None):
        pass

    def register_handler(self, handler):
        pass

    def disconnect(self, timeout=None):
        pass


class _FakeDash:
    def load_url(self, url, force=False):
        pass


def test_status_answers_while_a_connect_is_in_flight(monkeypatch, tmp_path):
    import pychromecast
    import pychromecast.controllers.dashcast as dashcast

    from app.services import cast as cast_module

    release = threading.Event()

    def slow_connect(host, timeout=None):
        release.wait(5)  # a Hub that takes its time to answer
        return _FakeCast()

    monkeypatch.setattr(pychromecast, "get_chromecast_from_host", slow_connect)
    monkeypatch.setattr(dashcast, "DashCastController", _FakeDash)
    monkeypatch.setattr(cast_module, "_SETTINGS_PATH", tmp_path / "cast.json")
    monkeypatch.setattr(cast_module.time, "sleep", lambda s: None)

    manager = cast_module.CastManager()
    manager._devices = {
        "00000000-0000-0000-0000-000000000001": {
            "uuid": "00000000-0000-0000-0000-000000000001",
            "name": "Hub",
            "model": "Google Nest Hub",
            "host": "192.0.2.1",
            "port": 8009,
        }
    }

    worker = threading.Thread(
        target=manager.connect, kwargs={"uuid": "00000000-0000-0000-0000-000000000001"}
    )
    worker.start()
    time.sleep(0.2)  # connect is now blocked inside slow_connect

    started = time.perf_counter()
    status = manager.status()
    elapsed = time.perf_counter() - started

    release.set()
    worker.join(5)

    assert elapsed < 0.5
    assert status["connected"] is False
    assert manager.status()["connected"] is True
