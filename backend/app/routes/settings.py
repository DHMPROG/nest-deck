"""Per-install app settings (onboarding flag, …)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ..services import settings as store

router = APIRouter(tags=["settings"])


class SettingsPatch(BaseModel):
    onboarded: bool | None = None


@router.get("/settings")
def get_settings() -> dict[str, Any]:
    return store.load()


@router.patch("/settings")
def patch_settings(body: SettingsPatch) -> dict[str, Any]:
    return store.update(body.model_dump(exclude_unset=True))
