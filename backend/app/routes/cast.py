"""Casting the Deck to a Chromecast / Nest Hub.

Used by the desktop app's cast panel: scan the LAN, connect (which casts the
Deck), check status, disconnect. Sync handlers so pychromecast's blocking calls
run in the threadpool.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.cast import cast_manager

router = APIRouter(tags=["cast"])


class ConnectBody(BaseModel):
    uuid: str | None = None
    name: str | None = None


@router.get("/cast/devices")
def scan_devices(timeout: int = 6):
    """Discover Cast devices on the network (blocks for `timeout` seconds)."""
    return {
        "devices": cast_manager.scan(timeout=timeout),
        "remembered": cast_manager.remembered(),
    }


@router.get("/cast/status")
def cast_status():
    return cast_manager.status()


@router.post("/cast/connect")
def cast_connect(body: ConnectBody):
    if not body.uuid and not body.name:
        raise HTTPException(422, "uuid ou name requis")
    try:
        return cast_manager.connect(uuid=body.uuid, name=body.name)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"échec de la connexion : {exc}")


@router.post("/cast/recast")
def cast_recast():
    """Reload the Deck on the connected device (after a Hub sleep, say)."""
    try:
        return cast_manager.recast()
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"échec : {exc}")


@router.post("/cast/disconnect")
def cast_disconnect():
    cast_manager.disconnect()
    return {"connected": False}


@router.delete("/cast/remembered")
def cast_forget():
    """Stop auto-reconnecting to the saved device."""
    cast_manager.forget()
    return {"remembered": None}
