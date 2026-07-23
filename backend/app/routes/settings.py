"""Per-install app settings: onboarding flag + start-with-Windows."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..services import autostart
from ..services import settings as store

router = APIRouter(tags=["settings"])


class SettingsPatch(BaseModel):
    onboarded: bool | None = None
    autostart: bool | None = None
    # Applied at the next launch; ports below 1024 need admin to bind.
    port: int | None = Field(default=None, ge=1024, le=65535)


def _snapshot() -> dict[str, Any]:
    return {
        **store.load(),
        # Autostart is live OS state, not a stored preference.
        "autostart": autostart.is_enabled(),
        "autostart_supported": autostart.supported(),
    }


@router.get("/settings")
def get_settings() -> dict[str, Any]:
    return _snapshot()


@router.patch("/settings")
def patch_settings(body: SettingsPatch) -> dict[str, Any]:
    data = body.model_dump(exclude_unset=True)

    if "autostart" in data:
        if data.pop("autostart"):
            autostart.enable()
        else:
            autostart.disable()

    if data:
        store.update(data)

    return _snapshot()
