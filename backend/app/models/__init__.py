from datetime import datetime, timezone

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MovieTag(SQLModel, table=True):
    movie_id: int | None = Field(default=None, foreign_key="movie.id", primary_key=True, ondelete="CASCADE")
    tag_id: int | None = Field(default=None, foreign_key="tag.id", primary_key=True, ondelete="CASCADE")


class CollectionMovie(SQLModel, table=True):
    collection_id: int | None = Field(default=None, foreign_key="collection.id", primary_key=True, ondelete="CASCADE")
    movie_id: int | None = Field(default=None, foreign_key="movie.id", primary_key=True, ondelete="CASCADE")


class Movie(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("relative_path", name="uq_movie_relative_path"),)

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True, max_length=300)
    original_title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, sa_column=Column(Text))
    release_year: int | None = Field(default=None, index=True)
    duration_seconds: float | None = None
    relative_path: str = Field(index=True, max_length=1200)
    file_size: int = Field(default=0, index=True)
    file_mtime_ns: int = 0
    file_extension: str = Field(default="", max_length=16)
    video_codec: str | None = Field(default=None, max_length=80)
    audio_codec: str | None = Field(default=None, max_length=80)
    resolution: str | None = Field(default=None, max_length=40)
    poster_path: str | None = Field(default=None, max_length=1200)
    backdrop_path: str | None = Field(default=None, max_length=1200)
    tmdb_id: int | None = Field(default=None, index=True)
    genres: str | None = Field(default=None, max_length=500)
    metadata_edited: bool = False
    is_favorite: bool = Field(default=False, index=True)
    is_watched: bool = Field(default=False, index=True)
    is_available: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)

    tags: list["Tag"] = Relationship(back_populates="movies", link_model=MovieTag)
    collections: list["Collection"] = Relationship(back_populates="movies", link_model=CollectionMovie)
    # Keep the forward relationship name simple for SQLAlchemy's resolver.
    # The relation may be absent even though the ORM annotation names its target.
    progress: "WatchProgress" = Relationship(
        back_populates="movie", cascade_delete=True, sa_relationship_kwargs={"uselist": False}
    )


class Tag(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("name", name="uq_tag_name"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=80)
    color: str = Field(default="#7c3aed", max_length=20)
    created_at: datetime = Field(default_factory=utcnow)
    movies: list[Movie] = Relationship(back_populates="tags", link_model=MovieTag)


class Collection(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("name", name="uq_collection_name"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=120)
    description: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow)
    movies: list[Movie] = Relationship(back_populates="collections", link_model=CollectionMovie)


class WatchProgress(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("movie_id", name="uq_progress_movie"),)

    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movie.id", index=True, ondelete="CASCADE")
    position_seconds: float = 0
    completed: bool = False
    last_watched_at: datetime = Field(default_factory=utcnow, index=True)
    movie: Movie = Relationship(back_populates="progress")

