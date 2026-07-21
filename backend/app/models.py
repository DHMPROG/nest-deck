"""SQLModel tables.

Relationship shape:
    PROFILE 1--* PAGE 1--* TILE *--1 ACTION *--1 CATEGORY
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ActionType(str, Enum):
    """Dispatch key into ``services.registry.HANDLERS``."""

    demo = "demo"
    fetch = "fetch"
    obs = "obs"
    spotify = "spotify"
    pc = "pc"
    meeting = "meeting"
    launcher = "launcher"
    open = "open"


class Category(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    # One of the 5 design tokens: stream / pc / games / meeting / media
    color: str
    icon: str


class Action(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    category_id: str = Field(foreign_key="category.id", index=True)
    label: str
    icon: str
    type: ActionType = Field(default=ActionType.demo)
    # URL for `fetch`, command for `launcher`, ws target for `obs`, ...
    endpoint: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Profile(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    icon: str = "house"
    # Exactly one profile carries active=True; enforced by the activate route.
    active: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=_now)


class Page(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    profile_id: str = Field(foreign_key="profile.id", index=True)
    name: str
    color: str
    position: int = 0
    icon: str = "square"
    # Grid geometry is per page, between MIN_ROWS x MIN_COLS and MAX_*.
    rows: int = Field(default=3)
    cols: int = Field(default=5)


class Tile(SQLModel, table=True):
    """A slot in the 5x3 grid. ``action_id=None`` means an empty slot."""

    __table_args__ = (UniqueConstraint("page_id", "row", "col", name="uq_tile_slot"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    page_id: str = Field(foreign_key="page.id", index=True)
    action_id: Optional[str] = Field(default=None, foreign_key="action.id")
    row: int  # 0-2
    col: int  # 0-4
    custom_label: Optional[str] = None
    custom_icon: Optional[str] = None


# Grid geometry. 5x3 is the default that fits the Nest Hub's 1280x800 panel
# comfortably; anything denser is allowed up to 6x6, past which the tiles stop
# being reliable touch targets.
GRID_ROWS = 3
GRID_COLS = 5
MIN_ROWS, MAX_ROWS = 3, 6
MIN_COLS, MAX_COLS = 5, 6
