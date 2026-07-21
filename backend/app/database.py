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


def _add_missing_columns() -> None:
    """Add columns that exist on the models but not yet in the file.

    `create_all` only creates missing *tables*, so a database from an earlier
    version keeps its old shape and every query against a new column fails.
    This is a deliberately small stand-in for a migration tool: additive only,
    with a default, which covers every schema change made so far.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table in SQLModel.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # create_all will handle it
            present = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present or column.default is None:
                    continue
                default = column.default.arg
                literal = f"'{default}'" if isinstance(default, str) else int(default)
                connection.execute(
                    text(
                        f'ALTER TABLE "{table.name}" '
                        f'ADD COLUMN "{column.name}" {column.type} '
                        f"NOT NULL DEFAULT {literal}"
                    )
                )


def init_db() -> None:
    """Create all tables, then patch in any newly added column."""
    # Importing models registers them on SQLModel.metadata.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _add_missing_columns()


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    with Session(engine) as session:
        yield session
