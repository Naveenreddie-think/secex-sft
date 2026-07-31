"""
Shared pytest fixtures. Ensures the database schema exists before any test
runs, regardless of whether the app's lifespan startup event fires (it won't,
since tests use TestClient without entering it as a context manager).
"""

import pytest

from app.db import Base, engine


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield