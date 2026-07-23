"""App-level settings persisted as a small JSON file in the data dir.

Distinct from the deck config in SQLite: these are per-install preferences the
desktop app needs, starting with whether onboarding has run. Server-side rather
than in the browser so "first launch" is true once per machine, whatever client
opens it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..database import data_dir

_PATH = Path(os.environ.get("APP_SETTINGS", str(data_dir() / "settings.json")))

_DEFAULTS: dict[str, Any] = {
    "onboarded": False,
    # The port the desktop app serves on. Read by the launcher at boot, so a
    # change only takes effect after a restart.
    "port": 8770,
}


def load() -> dict[str, Any]:
    try:
        stored = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        stored = {}
    return {**_DEFAULTS, **stored}


def update(patch: dict[str, Any]) -> dict[str, Any]:
    current = load()
    current.update(patch)
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        _PATH.write_text(json.dumps(current), encoding="utf-8")
    except OSError:
        pass  # a read-only data dir must not break the app
    return current
