import shutil
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.models import Movie
from app.services.media import inspect_media
from app.services.paths import safe_movie_path

router = APIRouter(prefix="/metadata", tags=["metadata"])
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"


@router.get("/tmdb/search")
async def tmdb_search(query: str, year: int | None = None, settings: Settings = Depends(get_settings)):
    if not settings.tmdb_api_key:
        raise HTTPException(status_code=503, detail="TMDB is not configured")
    params = {"api_key": settings.tmdb_api_key, "query": query, "include_adult": "false"}
    if year:
        params["year"] = str(year)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{TMDB_BASE}/search/movie", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="TMDB is currently unavailable") from exc


async def _cache_tmdb_image(client: httpx.AsyncClient, remote_path: str | None, destination: Path) -> str | None:
    if not remote_path:
        return None
    response = await client.get(f"{TMDB_IMAGE_BASE}{remote_path}")
    response.raise_for_status()
    if len(response.content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="TMDB artwork is unexpectedly large")
    destination.write_bytes(response.content)
    return destination.name


@router.post("/movies/{movie_id}/tmdb/{tmdb_id}")
async def apply_tmdb_match(
    movie_id: int,
    tmdb_id: int,
    overwrite: bool = False,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    movie = session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    if not settings.tmdb_api_key:
        raise HTTPException(status_code=503, detail="TMDB is not configured")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{TMDB_BASE}/movie/{tmdb_id}", params={"api_key": settings.tmdb_api_key}
            )
            response.raise_for_status()
            data = response.json()
            settings.artwork_dir.mkdir(parents=True, exist_ok=True)
            poster = await _cache_tmdb_image(client, data.get("poster_path"), settings.artwork_dir / f"movie-{movie_id}-tmdb.jpg")
            backdrop = await _cache_tmdb_image(client, data.get("backdrop_path"), settings.artwork_dir / f"movie-{movie_id}-backdrop.jpg")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="TMDB is currently unavailable") from exc
    movie.tmdb_id = tmdb_id
    if not movie.metadata_edited or overwrite:
        movie.title = data.get("title") or movie.title
        movie.original_title = data.get("original_title")
        movie.description = data.get("overview") or movie.description
        release_date = data.get("release_date") or ""
        movie.release_year = int(release_date[:4]) if len(release_date) >= 4 else movie.release_year
        movie.genres = ", ".join(item["name"] for item in data.get("genres", [])) or movie.genres
    if poster:
        movie.poster_path = poster
    if backdrop:
        movie.backdrop_path = backdrop
    session.add(movie)
    session.commit()
    session.refresh(movie)
    return movie


@router.post("/movies/{movie_id}/inspect")
def inspect_movie(movie_id: int, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    movie = session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    try:
        path = safe_movie_path(settings.movie_root, movie.relative_path)
        details = inspect_media(path, settings.ffprobe_path)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Media inspection failed: {exc}") from exc
    for key, value in details.items():
        setattr(movie, key, value)
    session.add(movie)
    session.commit()
    session.refresh(movie)
    return movie


@router.post("/movies/{movie_id}/poster")
def upload_poster(
    movie_id: int,
    poster: UploadFile = File(...),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    movie = session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    allowed = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    if poster.content_type not in allowed:
        raise HTTPException(status_code=415, detail="Poster must be JPEG, PNG, or WebP")
    settings.artwork_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.artwork_dir / f"movie-{movie_id}{allowed[poster.content_type]}"
    with destination.open("wb") as output:
        shutil.copyfileobj(poster.file, output, length=1024 * 1024)
    movie.poster_path = destination.name
    movie.metadata_edited = True
    session.add(movie)
    session.commit()
    return {"poster_path": movie.poster_path}

