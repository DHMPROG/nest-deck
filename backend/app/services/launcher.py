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
import shlex
import subprocess
import sys

from ..models import Action


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
            # Split like a shell would, but still run without one.
            parts = shlex.split(str(launch), posix=sys.platform != "win32")
            if not parts:
                return {"status": "error", "message": "empty command"}
            await asyncio.to_thread(_spawn, parts, False)
            label = parts[0]
        else:
            return {"status": "error", "message": "nothing to launch"}

        return {"status": "ok", "message": f"lancé · {label}"}

    except FileNotFoundError:
        return {"status": "error", "message": "commande introuvable"}
    except PermissionError:
        return {"status": "error", "message": "permission refusée"}
    except Exception as exc:  # noqa: BLE001 - handlers must never raise
        return {"status": "error", "message": str(exc) or type(exc).__name__}
