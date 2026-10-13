from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func
from sqlmodel import Session, select

from app.core.database import get_session
from app.models import Movie, MovieTag, Tag, WatchProgress
from app.schemas import BulkTagUpdate, MovieUpdate, ProgressUpdate

router = APIRouter(prefix="/movies", tags=["movies"])


def serialize_movie(movie: Movie) -> dict:
    return {
        **movie.model_dump(),
        "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in movie.tags],
        "progress": movie.progress.model_dump() if movie.progress else None,
    }


@router.get("")
def list_movies(
    session: Session = Depends(get_session),
    search: str | None = None,
    tags: list[int] = Query(default=[]),
    genre: str | None = None,
    year: int | None = None,
    watched: bool | None = None,
    favorite: bool | None = None,
    available: bool | None = None,
    sort: Literal["title", "release_year", "created_at", "file_size"] = "title",
    order: Literal["asc", "desc"] = "asc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=48, ge=1, le=200),
) -> dict:
    statement = select(Movie)
    count_statement = select(func.count(Movie.id))
    filters = []
    if search:
        filters.append(Movie.title.ilike(f"%{search}%"))
    if genre:
        filters.append(Movie.genres.ilike(f"%{genre}%"))
    if year is not None:
        filters.append(Movie.release_year == year)
    if watched is not None:
        filters.append(Movie.is_watched == watched)
    if favorite is not None:
        filters.append(Movie.is_favorite == favorite)
    if available is not None:
        filters.append(Movie.is_available == available)
    if tags:
        tagged_ids = (
            select(MovieTag.movie_id)
            .where(MovieTag.tag_id.in_(tags))
            .group_by(MovieTag.movie_id)
            .having(func.count(MovieTag.tag_id) == len(set(tags)))
        )
        filters.append(Movie.id.in_(tagged_ids))
    for condition in filters:
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    sort_column = getattr(Movie, sort)
    statement = statement.order_by((desc if order == "desc" else asc)(sort_column), Movie.id)
    total = session.exec(count_statement).one()
    items = session.exec(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [serialize_movie(item) for item in items], "total": total, "page": page, "page_size": page_size}


@router.get("/{movie_id}")
def get_movie(movie_id: int, session: Session = Depends(get_session)) -> dict:
    movie = session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    data = serialize_movie(movie)
    data["collections"] = [{"id": item.id, "name": item.name} for item in movie.collections]
    return data


@router.patch("/{movie_id}")
def update_movie(movie_id: int, payload: MovieUpdate, session: Session = Depends(get_session)) -> dict:
    movie = session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(movie, key, value)
    if any(key not in {"is_favorite", "is_watched"} for key in changes):
        movie.metadata_edited = True
    movie.updated_at = datetime.now(timezone.utc)
    session.add(movie)
    session.commit()
    session.refresh(movie)
    return serialize_movie(movie)


@router.put("/{movie_id}/progress")
def save_progress(movie_id: int, payload: ProgressUpdate, session: Session = Depends(get_session)) -> dict:
    movie = session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    progress = session.exec(select(WatchProgress).where(WatchProgress.movie_id == movie_id)).first()
    if not progress:
        progress = WatchProgress(movie_id=movie_id)
    progress.position_seconds = payload.position_seconds
    progress.completed = payload.completed
    progress.last_watched_at = datetime.now(timezone.utc)
    if payload.completed:
        movie.is_watched = True
        session.add(movie)
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress.model_dump()


@router.post("/bulk/tags")
def bulk_tags(payload: BulkTagUpdate, session: Session = Depends(get_session)) -> dict:
    movies = session.exec(select(Movie).where(Movie.id.in_(payload.movie_ids))).all()
    tag_objects = session.exec(select(Tag).where(Tag.id.in_(payload.tag_ids))).all()
    if len(movies) != len(set(payload.movie_ids)) or len(tag_objects) != len(set(payload.tag_ids)):
        raise HTTPException(status_code=404, detail="One or more movies or tags were not found")
    for movie in movies:
        if payload.operation == "add":
            existing = {tag.id for tag in movie.tags}
            movie.tags.extend(tag for tag in tag_objects if tag.id not in existing)
        else:
            remove_ids = {tag.id for tag in tag_objects}
            movie.tags = [tag for tag in movie.tags if tag.id not in remove_ids]
        session.add(movie)
    session.commit()
    return {"updated": len(movies)}

