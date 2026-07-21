"""Subprocess launcher.

Params shape:
    {"launch": "steam"}
    {"args": ["code", "--new-window"]}
    {"shell": "explorer.exe C:/Users"}      # opt in explicitly

`action.endpoint` is used when no params are given.

The process is spawned detached and never awaited: a deck button starts an app,
it does not wait for it to exit.

Note this executes whatever the catalog says, by design — the spec's threat
model is a single-user app on a trusted LAN with no authentication. Anyone who
can reach the API can already reconfigure every tile.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from ..models import Action

# Where Windows records what is actually installed. `steam`, `discord` and the
# like are never on PATH, so resolving a bare name means looking here.
_START_MENU_ROOTS = [
    Path(os.environ.get("ProgramData", "")) / "Microsoft/Windows/Start Menu/Programs",
    Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
]

_IGNORED = {"uninstall", "désinstaller", "readme", "lisez-moi", "aide", "help", "manual"}


@lru_cache(maxsize=1)
def installed_apps() -> list[dict]:
    """Applications discovered from the Start Menu, sorted by name.

    Cached: scanning a few hundred shortcuts on every keystroke of the Editor's
    picker would be wasteful. Call `refresh_apps()` after installing something.
    """
    found: dict[str, dict] = {}

    for root in _START_MENU_ROOTS:
        if not root.exists():
            continue
        for link in root.rglob("*.lnk"):
            name = link.stem
            lowered = name.lower()
            if any(word in lowered for word in _IGNORED):
                continue
            # First one wins; ProgramData is scanned before the user profile.
            found.setdefault(lowered, {"name": name, "path": str(link)})

    return sorted(found.values(), key=lambda a: a["name"].lower())


def refresh_apps() -> None:
    installed_apps.cache_clear()


def resolve_target(target: str) -> str | None:
    """Turn what the user typed into something launchable.

    Order: an existing path, then PATH, then the name of an installed app.
    Returns None when nothing matches.
    """
    candidate = target.strip().strip('"')
    if not candidate:
        return None

    if Path(candidate).exists():
        return candidate

    on_path = shutil.which(candidate)
    if on_path:
        return on_path

    lowered = candidate.lower()
    apps = installed_apps()
    for app in apps:  # exact name first
        if app["name"].lower() == lowered:
            return app["path"]
    for app in apps:  # then a prefix, so "steam" finds "Steam"
        if app["name"].lower().startswith(lowered):
            return app["path"]
    for app in apps:
        if lowered in app["name"].lower():
            return app["path"]
    return None


def _spawn(args: list[str] | str, shell: bool) -> None:
    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "shell": shell,
    }
    if sys.platform == "win32":
        # Detach so the app outlives the request and shows no console window.
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen(args, **kwargs)


async def handle(action: Action) -> dict:
    params = action.params or {}

    shell_command = params.get("shell")
    args = params.get("args")
    launch = params.get("launch") or action.endpoint

    try:
        if shell_command:
            await asyncio.to_thread(_spawn, str(shell_command), True)
            label = str(shell_command)
        elif args:
            if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
                return {"status": "error", "message": "args must be a list of strings"}
            await asyncio.to_thread(_spawn, args, False)
            label = args[0]
        elif launch:
            resolved = await asyncio.to_thread(resolve_target, str(launch))
            if resolved is None:
                return {
                    "status": "error",
                    "message": f"« {launch} » introuvable — choisissez l'application dans la liste",
                }

            if sys.platform == "win32":
                # startfile follows shell associations, which is what makes a
                # Start Menu .lnk launchable at all.
                await asyncio.to_thread(os.startfile, resolved)
            else:
                parts = shlex.split(resolved, posix=True)
                await asyncio.to_thread(_spawn, parts or [resolved], False)

            label = Path(resolved).stem or str(launch)
        else:
            return {"status": "error", "message": "nothing to launch"}

        return {"status": "ok", "message": f"lancé · {label}"}

    except FileNotFoundError:
        return {"status": "error", "message": "commande introuvable"}
    except PermissionError:
        return {"status": "error", "message": "permission refusée"}
    except Exception as exc:  # noqa: BLE001 - handlers must never raise
        return {"status": "error", "message": str(exc) or type(exc).__name__}
