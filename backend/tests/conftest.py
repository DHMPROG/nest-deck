"""Every test gets a fresh, freshly seeded database in a temp dir.

The data dir is read when `app.database` is imported, so it is set before any
app import — and the app is imported inside the fixture, never at module level.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["NESTDECK_DATA"] = tempfile.mkdtemp(prefix="nestdeck-test-")
os.environ.pop("DATABASE_URL", None)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from sqlmodel import SQLModel

    from app.database import engine
    from app.main import app

    SQLModel.metadata.drop_all(engine)
    # The guard only lets local hosts through; TestClient's default "testserver" is not one.
    with TestClient(app, base_url="http://127.0.0.1:8770") as test_client:
        yield test_client
