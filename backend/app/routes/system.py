"""Host introspection for the Editor's launcher picker.

Not in the spec's route list, but typing a program name is guesswork — `steam`
and `discord` are never on PATH — so the Editor needs to see what is actually
installed, and to browse for anything the Start Menu missed.

Read-only, and scoped to listing: nothing here executes or modifies anything.
It does expose directory names to the LAN, which matches the spec's threat
model (single user, trusted network, no auth) — anyone who can reach the API
can already reconfigure every tile.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..services.launcher import installed_apps, refresh_apps

router = APIRouter(tags=["system"])

LAUNCHABLE_SUFFIXES = {".exe", ".lnk", ".bat", ".cmd", ".com", ".url"}
MAX_ENTRIES = 400


@router.get("/system/apps")
def list_apps(
    q: Optional[str] = Query(None, description="Case-insensitive name filter"),
    refresh: bool = Query(False, description="Rescan instead of using the cache"),
):
    """Applications found in the Start Menu."""
    if refresh:
        refresh_apps()

    apps = installed_apps()
    if q:
        needle = q.strip().lower()
        apps = [a for a in apps if needle in a["name"].lower()]
    return apps[:MAX_ENTRIES]


@router.get("/system/browse")
def browse(path: Optional[str] = Query(None, description="Directory to list")):
    """List directories and launchable files, for a simple file picker."""
    if not path:
        # Sensible starting points rather than dumping the whole filesystem.
        roots = []
        if sys.platform == "win32":
            for letter in "CDEFGH":
                drive = Path(f"{letter}:/")
                if drive.exists():
                    roots.append({"name": f"{letter}:", "path": str(drive), "kind": "dir"})
            for label, env in (
                ("Program Files", "ProgramFiles"),
                ("Program Files (x86)", "ProgramFiles(x86)"),
                ("Bureau", None),
            ):
                target = (
                    Path(os.environ[env])
                    if env and os.environ.get(env)
                    else Path.home() / "Desktop"
                )
                if target.exists():
                    roots.append({"name": label, "path": str(target), "kind": "dir"})
        else:
            for target in (Path("/usr/bin"), Path("/opt"), Path.home()):
                if target.exists():
                    roots.append({"name": str(target), "path": str(target), "kind": "dir"})
        return {"path": None, "parent": None, "entries": roots}

    current = Path(path)
    if not current.exists() or not current.is_dir():
        raise HTTPException(404, "dossier introuvable")

    entries = []
    try:
        for child in sorted(
            current.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower())
        ):
            if child.name.startswith("."):
                continue
            try:
                if child.is_dir():
                    entries.append({"name": child.name, "path": str(child), "kind": "dir"})
                elif child.suffix.lower() in LAUNCHABLE_SUFFIXES:
                    entries.append({"name": child.name, "path": str(child), "kind": "file"})
            except OSError:
                continue  # unreadable entry, skip it
            if len(entries) >= MAX_ENTRIES:
                break
    except PermissionError:
        raise HTTPException(403, "accès refusé à ce dossier")

    parent = str(current.parent) if current.parent != current else None
    return {"path": str(current), "parent": parent, "entries": entries}
