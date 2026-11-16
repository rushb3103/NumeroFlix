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



def test_category_filter_and_thumbnail_timestamp(test_context):
    client, session, _ = test_context
    movie = Movie(title="Selected", relative_path="selected.mp4", duration_seconds=600)
    other = Movie(title="Other", relative_path="other.mp4")
    session.add_all([movie, other])
    session.commit()
    session.refresh(movie)
    category = client.post("/api/collections", json={"name": "Favorites"}).json()
    assert client.post(f"/api/collections/{category['id']}/movies", json={"movie_ids": [movie.id]}).status_code == 200
    result = client.get("/api/movies", params={"category": category["id"]}).json()
    assert [item["title"] for item in result["items"]] == ["Selected"]
    assert client.patch(f"/api/movies/{movie.id}", json={"title": "Renamed", "thumbnail_seconds": 30}).status_code == 200
    assert client.get(f"/api/movies/{movie.id}").json()["thumbnail_seconds"] == 30
    assert client.patch(f"/api/movies/{movie.id}", json={"thumbnail_seconds": 600}).status_code == 422
    assert client.patch(f"/api/movies/{movie.id}", json={"thumbnail_seconds": None}).json()["thumbnail_seconds"] is None


def test_admin_video_upload_and_delete(test_context):
    client, session, root = test_context
    upload = client.post("/api/library/videos", files={"video": ("Example.2020.mp4", b"video bytes", "video/mp4")})
    assert upload.status_code == 201
    movie_id = upload.json()["id"]
    assert (root / "Example.2020.mp4").read_bytes() == b"video bytes"
    assert client.get(f"/api/movies/{movie_id}").json()["title"] == "Example"
    assert client.post("/api/library/videos", files={"video": ("Example.2020.mp4", b"other", "video/mp4")}).status_code == 409
    assert (root / "Example.2020.mp4").read_bytes() == b"video bytes"
    assert client.delete(f"/api/library/videos/{movie_id}").status_code == 204
    assert not (root / "Example.2020.mp4").exists()
    assert client.get(f"/api/movies/{movie_id}").status_code == 404


def test_admin_video_rejects_unsafe_filenames_and_paths(test_context):
    client, session, root = test_context
    assert client.post("/api/library/videos", files={"video": ("../escape.mp4", b"x", "video/mp4")}).status_code == 400
    assert client.post("/api/library/videos", files={"video": ("bad.txt", b"x", "text/plain")}).status_code == 415
    outside = root.parent / "outside.mp4"
    outside.write_bytes(b"keep")
    movie = Movie(title="Unsafe", relative_path="../outside.mp4")
    session.add(movie)
    session.commit()
    session.refresh(movie)
    assert client.delete(f"/api/library/videos/{movie.id}").status_code == 403
    assert outside.read_bytes() == b"keep"
    assert session.get(Movie, movie.id) is not None


def test_chunked_video_upload_and_cleanup(test_context):
    client, _, root = test_context
    start = client.post('/api/library/uploads', json={'filename': 'chunks.mp4', 'size': 6})
    assert start.status_code == 201
    upload_id = start.json()['id']
    headers = {'Content-Type': 'application/octet-stream'}
    assert client.put(f'/api/library/uploads/{upload_id}?offset=0', content=b'abc', headers=headers).json()['received'] == 3
    assert client.put(f'/api/library/uploads/{upload_id}?offset=0', content=b'def', headers=headers).status_code == 409
    assert client.post(f'/api/library/uploads/{upload_id}/complete').status_code == 409
    assert client.put(f'/api/library/uploads/{upload_id}?offset=3', content=b'def', headers=headers).status_code == 200
    complete = client.post(f'/api/library/uploads/{upload_id}/complete')
    assert complete.status_code == 201
    assert (root / 'chunks.mp4').read_bytes() == b'abcdef'
    assert client.post(f'/api/library/uploads/{upload_id}/complete').status_code == 404
    cancelled = client.post('/api/library/uploads', json={'filename': 'cancel.mp4', 'size': 1}).json()['id']
    assert client.delete(f'/api/library/uploads/{cancelled}').status_code == 204
    assert client.put(f'/api/library/uploads/{cancelled}?offset=0', content=b'x', headers=headers).status_code == 404
