from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app


@pytest.fixture
def test_context(tmp_path: Path) -> Generator[tuple[TestClient, Session, Path], None, None]:
    movie_root = tmp_path / "movies"
    movie_root.mkdir()
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(test_engine)
    session = Session(test_engine)
    settings = Settings(movie_root=movie_root, database_url="sqlite://", artwork_dir=tmp_path / "artwork", cache_dir=tmp_path / "cache")

    def session_override():
        yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client, session, movie_root
    app.dependency_overrides.clear()
    session.close()

