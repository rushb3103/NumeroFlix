import importlib

from sqlmodel import select

from app.core.config import Settings, get_settings
from app.main import app
from app.models import Movie, Tag, WatchProgress


def test_health_and_tag_crud(test_context):
    client, _, _ = test_context
    assert client.get("/health").json() == {"status": "ok"}
    created = client.post("/api/tags", json={"name": "Comfort", "color": "#112233"})
    assert created.status_code == 201
    tag_id = created.json()["id"]
    assert client.put(f"/api/tags/{tag_id}", json={"name": "Cozy", "color": "#334455"}).status_code == 200
    assert client.delete(f"/api/tags/{tag_id}").status_code == 204


def test_search_filters_and_progress(test_context):
    client, session, _ = test_context
    movie = Movie(title="Moon", release_year=2009, relative_path="moon.mp4", file_extension=".mp4")
    session.add(movie)
    session.commit()
    session.refresh(movie)
    result = client.get("/api/movies", params={"search": "moo", "year": 2009}).json()
    assert result["total"] == 1
    response = client.put(f"/api/movies/{movie.id}/progress", json={"position_seconds": 42, "completed": False})
    assert response.status_code == 200
    assert session.exec(select(WatchProgress)).one().position_seconds == 42


def test_streaming_ranges_and_head(test_context):
    client, session, root = test_context
    (root / "sample.mp4").write_bytes(b"0123456789")
    movie = Movie(title="Sample", relative_path="sample.mp4", file_size=10, file_extension=".mp4")
    session.add(movie)
    session.commit()
    session.refresh(movie)
    response = client.get(f"/api/movies/{movie.id}/stream", headers={"Range": "bytes=2-5"})
    assert response.status_code == 206
    assert response.content == b"2345"
    assert response.headers["content-range"] == "bytes 2-5/10"
    assert client.head(f"/api/movies/{movie.id}/stream").headers["content-length"] == "10"
    assert client.get(f"/api/movies/{movie.id}/stream", headers={"Range": "bytes=20-30"}).status_code == 416


def test_path_traversal_is_rejected(test_context):
    client, session, root = test_context
    (root.parent / "secret.mp4").write_bytes(b"secret")
    movie = Movie(title="Invalid", relative_path="../secret.mp4", file_extension=".mp4")
    session.add(movie)
    session.commit()
    session.refresh(movie)
    assert client.get(f"/api/movies/{movie.id}/stream").status_code == 403


def test_master_password_protects_api_and_uses_http_only_cookie(test_context, monkeypatch):
    client, _, root = test_context
    protected_settings = Settings(
        movie_root=root,
        database_url="sqlite://",
        artwork_dir=root.parent / "artwork",
        cache_dir=root.parent / "cache",
        master_password="correct horse battery staple",
    )
    main_module = importlib.import_module("app.main")
    monkeypatch.setattr(main_module, "settings", protected_settings)
    app.dependency_overrides[get_settings] = lambda: protected_settings

    assert client.get("/api/movies").status_code == 401
    assert client.post("/api/auth/login", json={"password": "wrong"}).status_code == 401
    login = client.post("/api/auth/login", json={"password": "correct horse battery staple"})
    assert login.status_code == 200
    assert "httponly" in login.headers["set-cookie"].lower()
    assert client.get("/api/movies").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/movies").status_code == 401


def test_movie_filter_requires_all_selected_tags(test_context):
    client, session, _ = test_context
    action = Tag(name="Action", color="#112233")
    classic = Tag(name="Classic", color="#445566")
    both = Movie(title="Both", relative_path="both.mp4", file_extension=".mp4", tags=[action, classic])
    one = Movie(title="One", relative_path="one.mp4", file_extension=".mp4", tags=[action])
    session.add(both)
    session.add(one)
    session.commit()
    session.refresh(action)
    session.refresh(classic)

    response = client.get("/api/movies", params=[("tags", action.id), ("tags", classic.id)])
    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["Both"]

