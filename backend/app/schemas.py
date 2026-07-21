"""Request bodies, response payloads and serialization helpers."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel
from sqlmodel import Session

from .models import Action, ActionType, Tile

# --------------------------------------------------------------------------- #
# Request bodies
# --------------------------------------------------------------------------- #


class ProfileCreate(BaseModel):
    name: str
    icon: str = "house"


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None


class PageCreate(BaseModel):
    profile_id: str
    name: str
    color: str
    icon: str = "square"
    position: Optional[int] = None


class PageUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    position: Optional[int] = None


class PositionUpdate(BaseModel):
    position: int


class CategoryCreate(BaseModel):
    name: str
    # One of the five design tokens; the Deck falls back to `pc` if unknown.
    color: str = "pc"
    icon: str = "folder"


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class ActionCreate(BaseModel):
    category_id: str
    label: str
    icon: str = "lightning"
    type: ActionType = ActionType.demo
    endpoint: Optional[str] = None
    params: dict[str, Any] = {}


class ActionUpdate(BaseModel):
    category_id: Optional[str] = None
    label: Optional[str] = None
    icon: Optional[str] = None
    type: Optional[ActionType] = None
    endpoint: Optional[str] = None
    params: Optional[dict[str, Any]] = None


class TileCreate(BaseModel):
    page_id: str
    row: int
    col: int
    action_id: Optional[str] = None
    custom_label: Optional[str] = None
    custom_icon: Optional[str] = None


class TileUpdate(BaseModel):
    row: Optional[int] = None
    col: Optional[int] = None
    action_id: Optional[str] = None
    custom_label: Optional[str] = None
    custom_icon: Optional[str] = None


# --------------------------------------------------------------------------- #
# Response payloads
# --------------------------------------------------------------------------- #


class FireResult(BaseModel):
    status: str
    message: str
    duration_ms: int


# --------------------------------------------------------------------------- #
# Serializers
# --------------------------------------------------------------------------- #


def serialize_action(action: Optional[Action]) -> Optional[dict[str, Any]]:
    if action is None:
        return None
    return {
        "id": action.id,
        "category_id": action.category_id,
        "label": action.label,
        "icon": action.icon,
        "type": action.type.value if hasattr(action.type, "value") else action.type,
        "endpoint": action.endpoint,
        "params": action.params or {},
    }


def serialize_tile(session: Session, tile: Tile) -> dict[str, Any]:
    """Tile with its action inlined, so the Deck can render in one round-trip."""
    action = session.get(Action, tile.action_id) if tile.action_id else None
    return {
        "id": tile.id,
        "page_id": tile.page_id,
        "action_id": tile.action_id,
        "row": tile.row,
        "col": tile.col,
        "custom_label": tile.custom_label,
        "custom_icon": tile.custom_icon,
        "action": serialize_action(action),
    }


def serialize_slot(
    session: Session, row: int, col: int, tile: Optional[Tile]
) -> dict[str, Any]:
    """One of the 15 grid slots; ``tile`` is null for an empty slot."""
    return {
        "row": row,
        "col": col,
        "tile": serialize_tile(session, tile) if tile is not None else None,
    }
