from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#7c3aed", pattern=r"^#[0-9a-fA-F]{6}$")


class TagRead(TagCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class CollectionRead(CollectionCreate):
    id: int
    created_at: datetime
    movie_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class MovieUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    original_title: str | None = None
    description: str | None = None
    release_year: int | None = Field(default=None, ge=1888, le=2200)
    genres: str | None = None
    is_favorite: bool | None = None
    is_watched: bool | None = None


class ProgressUpdate(BaseModel):
    position_seconds: float = Field(ge=0)
    completed: bool = False


class BulkTagUpdate(BaseModel):
    movie_ids: list[int]
    tag_ids: list[int]
    operation: str = Field(pattern="^(add|remove)$")


class MembershipUpdate(BaseModel):
    movie_ids: list[int]

