from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    movie_root: Path = Path("./movies")
    database_url: str = "sqlite:///./data/movies.db"
    artwork_dir: Path = Path("./data/artwork")
    cache_dir: Path = Path("./data/cache")
    tmdb_api_key: str = ""
    master_password: str = ""
    session_hours: int = 12
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Keep the new application isolated from any legacy root-level Flask .env file.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("movie_root", "artwork_dir", "cache_dir", mode="before")
    @classmethod
    def expand_path(cls, value: str | Path) -> Path:
        return Path(value).expanduser()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

