"""OBS WebSocket handler (obsws-python).

Params shape:
    {"request": "SetCurrentProgramScene", "args": {"sceneName": "Camera"}}

Any obs-websocket v5 request works as is. One extra, ``ToggleSceneItem``
({"sceneName", "sourceName"}), shows or hides a source: OBS only exposes a
setter keyed by a numeric item id, which nobody should have to look up by hand.

`obsws-python` is synchronous and connects on construction, so the whole call
runs in a worker thread. A fresh client per request keeps things simple and
avoids holding a socket open against an OBS that may be closed most of the day;
the cost is one handshake per press, which is negligible on a LAN.

Where to connect: the action's own endpoint, else the address saved from the
Editor (settings.json), else the OBS_URL / OBS_PASSWORD environment.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional
from urllib.parse import urlparse

from ..models import Action
from . import settings

TIMEOUT_S = 3

# inputKind fragments of real audio devices across Windows, macOS and Linux.
_AUDIO_DEVICE_KINDS = ("wasapi", "coreaudio", "pulse", "alsa", "jack", "sck_audio")


def _connection(endpoint: Optional[str] = None) -> tuple[str, int, str]:
    stored = settings.load()
    raw = (
        endpoint
        or stored.get("obs_url")
        or os.environ.get("OBS_URL")
        or "ws://localhost:4455"
    )
    parsed = urlparse(raw if "//" in raw else f"ws://{raw}")
    password = stored.get("obs_password") or os.environ.get("OBS_PASSWORD", "")
    return parsed.hostname or "localhost", parsed.port or 4455, password


def _client(host: str, port: int, password: str):
    import obsws_python as obsws

    return obsws.ReqClient(host=host, port=port, password=password, timeout=TIMEOUT_S)


def _close(client) -> None:
    try:
        client.disconnect()
    except Exception:  # noqa: BLE001 - never let cleanup mask the result
        pass


def _toggle_scene_item(client, args: dict) -> bool:
    scene, source = args.get("sceneName"), args.get("sourceName")
    item_id = client.send(
        "GetSceneItemId", {"sceneName": scene, "sourceName": source}, raw=True
    )["sceneItemId"]
    key = {"sceneName": scene, "sceneItemId": item_id}
    enabled = client.send("GetSceneItemEnabled", key, raw=True)["sceneItemEnabled"]
    client.send("SetSceneItemEnabled", {**key, "sceneItemEnabled": not enabled})
    return not enabled


def _call(host: str, port: int, password: str, request: str, args: dict) -> dict:
    client = _client(host, port, password)
    try:
        if request == "ToggleSceneItem":
            shown = _toggle_scene_item(client, args)
            return {
                "status": "ok",
                "message": f"OBS · {args.get('sourceName')} {'affiché' if shown else 'masqué'}",
            }
        client.send(request, args or None)
    finally:
        _close(client)
    return {"status": "ok", "message": f"OBS · {request}"}


def _reason(exc: BaseException) -> str:
    if isinstance(exc, ConnectionRefusedError):
        return "OBS fermé ou WebSocket désactivé"
    text = str(exc) or type(exc).__name__
    if "password" in text or "identify" in text:
        return "mot de passe WebSocket refusé"
    return text


async def handle(action: Action) -> dict:
    params = action.params or {}
    request = params.get("request")
    if not request:
        return {"status": "error", "message": "no OBS request configured"}

    host, port, password = _connection(action.endpoint)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                _call, host, port, password, request, params.get("args", {})
            ),
            timeout=TIMEOUT_S + 2,
        )
    except asyncio.TimeoutError:
        return {"status": "error", "message": f"OBS · timeout ({host}:{port})"}
    except ImportError:
        return {"status": "error", "message": "obsws-python not installed"}
    except Exception as exc:  # noqa: BLE001 - offline OBS must degrade, not crash
        return {"status": "error", "message": f"OBS · {_reason(exc)}"}


def _snapshot(host: str, port: int, password: str) -> dict[str, Any]:
    client = _client(host, port, password)
    try:
        version = client.send("GetVersion", raw=True)
        scene_list = client.send("GetSceneList", raw=True)
        # OBS lists scenes bottom-up; the Editor wants them as the dock shows them.
        scene_names = [s["sceneName"] for s in reversed(scene_list.get("scenes", []))]
        scenes = []
        for name in scene_names:
            items = client.send("GetSceneItemList", {"sceneName": name}, raw=True)
            scenes.append(
                {
                    "name": name,
                    "sources": [i["sourceName"] for i in items.get("sceneItems", [])],
                }
            )

        # Only inputs that carry audio can be muted, and GetInputMute fails on
        # the others. Probed through the base client, which reports the failure
        # instead of raising and logging a traceback per video source.
        inputs = client.send("GetInputList", raw=True).get("inputs", [])
        audio = [
            {
                "name": item["inputName"],
                # Mic / desktop / app capture, as opposed to a media file or
                # browser source that merely happens to have a soundtrack.
                "device": any(k in (item.get("inputKind") or "") for k in _AUDIO_DEVICE_KINDS),
            }
            for item in inputs
            if client.base_client.req("GetInputMute", {"inputName": item["inputName"]})
            .get("requestStatus", {})
            .get("result")
        ]
        audio.sort(key=lambda a: (not a["device"], a["name"].lower()))

        return {
            "connected": True,
            "address": f"{host}:{port}",
            "version": version.get("obsVersion"),
            "current_scene": scene_list.get("currentProgramSceneName"),
            "scenes": scenes,
            "audio_inputs": audio,
        }
    finally:
        _close(client)


async def snapshot() -> dict[str, Any]:
    """What the Editor needs to offer pickers: scenes, their sources, audio inputs."""
    host, port, password = _connection()
    offline: dict[str, Any] = {
        "connected": False,
        "address": f"{host}:{port}",
        "scenes": [],
        "audio_inputs": [],
    }
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_snapshot, host, port, password), timeout=TIMEOUT_S + 5
        )
    except asyncio.TimeoutError:
        return {**offline, "error": "OBS ne répond pas"}
    except ImportError:
        return {**offline, "error": "obsws-python n’est pas installé"}
    except Exception as exc:  # noqa: BLE001
        return {**offline, "error": _reason(exc)}
