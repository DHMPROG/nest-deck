"""Resource resolution that works both from source and once frozen.

PyInstaller unpacks bundled data under ``sys._MEIPASS`` at runtime; from source
the same paths are relative to the repo root. Both keep the layout
``frontend/build`` and ``desktop/assets`` so callers use one relative path.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Frozen: the onefile bundle's temp dir. Source: the repo root (parent of desktop/).
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def resource(relative: str) -> Path:
    return ROOT / relative
