"""Engine and session management.

The database is a single SQLite file. In Docker it lives at ``/data/deck.db``
(mounted volume); locally it defaults to ``<repo>/data/deck.db`` so that the
dev database and the container database occupy the same logical place.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

# <repo>/backend/app/database.py -> parents[2] == <repo>
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB_PATH = _REPO_ROOT / "data" / "deck.db"

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{_DEFAULT_DB_PATH}")

if DATABASE_URL.startswith("sqlite:///"):
    # Make sure the directory holding the SQLite file exists before connecting.
    db_path = Path(DATABASE_URL.removeprefix("sqlite:///"))
    db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create all tables. Safe to call on every boot."""
    # Importing models registers them on SQLModel.metadata.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    with Session(engine) as session:
        yield session
