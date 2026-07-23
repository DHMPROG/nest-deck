# PyInstaller spec for the Nest Deck desktop app.
#   pip install pyinstaller
#   pyinstaller NestDeck.spec          (from the repo root)
# Produces dist/NestDeck.exe — a single-file windowed executable.
#
# Build the frontend first: cd frontend && npm run build

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)  # noqa: F821 - injected by PyInstaller

# Make the backend package and the desktop modules importable during analysis.
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "desktop"))

datas = [
    (str(ROOT / "frontend" / "build"), "frontend/build"),
    (str(ROOT / "desktop" / "assets"), "desktop/assets"),
]
binaries = []
hiddenimports = []

# These pull data files and/or import submodules dynamically, so let
# PyInstaller collect everything rather than guessing.
for pkg in (
    "uvicorn",
    "pychromecast",
    "zeroconf",
    "webview",
    "sqlmodel",
    "sqlalchemy",
    "spotipy",
    "pynput",
    "obsws_python",
    "sse_starlette",
):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# The backend is imported via a runtime sys.path tweak; pull its whole tree
# (routes, services, handlers dispatched by name) so nothing is missed.
hiddenimports += collect_submodules("app")

a = Analysis(
    [str(ROOT / "desktop" / "nestdeck.py")],
    pathex=[str(ROOT / "backend"), str(ROOT / "desktop")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NestDeck",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "desktop" / "assets" / "NestDeck.ico"),
)
