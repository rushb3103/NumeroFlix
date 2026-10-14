import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from app.models import Movie, WatchProgress

SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}


def title_from_filename(path: Path) -> tuple[str, int | None]:
    cleaned = re.sub(r"[._]+", " ", path.stem)
    match = re.search(r"(?:^|\s)[\[(]?(19\d{2}|20\d{2})[\])]?(?:\s|$)", cleaned)
    year = int(match.group(1)) if match else None
    if match:
        cleaned = cleaned[: match.start()] or cleaned
    return re.sub(r"\s+", " ", cleaned).strip(), year


def normalized_path_key(relative_path: str) -> str:
    return relative_path.replace("\\", "/").casefold()


def content_identity(relative_path: str, file_size: int, file_mtime_ns: int) -> tuple[str, int, int]:
    # Copies in different vault folders commonly retain their filename and exact
    # byte size. This avoids expensive full-file hashing against remote storage.
    return Path(relative_path).name.casefold(), file_size, file_mtime_ns


def resolution_from_filename(path: Path) -> str | None:
    match = re.search(r"(?<!\d)(4320|2160|1440|1080|720|480)p(?!\d)", path.stem, re.IGNORECASE)
    return f"{match.group(1)}p" if match else None


def _merge_duplicate(session: Session, canonical: Movie, duplicate: Movie) -> None:
    existing_tag_ids = {tag.id for tag in canonical.tags}
    canonical.tags.extend(tag for tag in duplicate.tags if tag.id not in existing_tag_ids)
    existing_collection_ids = {item.id for item in canonical.collections}
    canonical.collections.extend(item for item in duplicate.collections if item.id not in existing_collection_ids)
    canonical.is_favorite = canonical.is_favorite or duplicate.is_favorite
    canonical.is_watched = canonical.is_watched or duplicate.is_watched
    canonical.is_available = canonical.is_available or duplicate.is_available
    if duplicate.metadata_edited and not canonical.metadata_edited:
        for field in ("title", "original_title", "description", "release_year", "poster_path", "backdrop_path", "tmdb_id", "genres"):
            setattr(canonical, field, getattr(duplicate, field))
        canonical.metadata_edited = True
    if duplicate.progress:
        if not canonical.progress:
            canonical.progress = WatchProgress(
                movie_id=canonical.id,
                position_seconds=duplicate.progress.position_seconds,
                completed=duplicate.progress.completed,
                last_watched_at=duplicate.progress.last_watched_at,
            )
            session.add(canonical.progress)
        elif duplicate.progress.last_watched_at > canonical.progress.last_watched_at:
            canonical.progress.position_seconds = duplicate.progress.position_seconds
            canonical.progress.completed = duplicate.progress.completed
            canonical.progress.last_watched_at = duplicate.progress.last_watched_at
            session.add(canonical.progress)
    session.add(canonical)
    session.delete(duplicate)


def scan_library(session: Session, root: Path, cancel: threading.Event | None = None, progress=None) -> dict:
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Movie root is unavailable: {root}")

    seen: set[str] = set()
    discovered = updated = errors = processed = duplicates_removed = duplicates_skipped = 0
    movies_by_key: dict[str, Movie] = {}
    movies_by_content: dict[tuple[str, int, int], Movie] = {}
    for existing in session.exec(select(Movie).order_by(Movie.id)).all():
        key = normalized_path_key(existing.relative_path)
        identity = content_identity(existing.relative_path, existing.file_size, existing.file_mtime_ns)
        canonical = movies_by_key.get(key) or movies_by_content.get(identity)
        if canonical:
            _merge_duplicate(session, canonical, existing)
            duplicates_removed += 1
            movies_by_key[key] = canonical
        else:
            movies_by_key[key] = existing
            movies_by_content[identity] = existing
    if duplicates_removed:
        session.flush()

    files = (path for path in root.rglob("*") if path.is_file() and not path.is_symlink())
    fallback_paths: dict[int, str] = {}
    for path in files:
        if cancel and cancel.is_set():
            return {"cancelled": True, "processed": processed, "discovered": discovered, "updated": updated, "duplicates_removed": duplicates_removed, "duplicates_skipped": duplicates_skipped, "errors": errors}
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            stat = path.stat()
            relative = path.relative_to(root).as_posix()
            key = normalized_path_key(relative)
            seen.add(key)
            movie = movies_by_key.get(key)
            action = "checked"
            if movie is None:
                identity = content_identity(relative, stat.st_size, stat.st_mtime_ns)
                duplicate_of = movies_by_content.get(identity)
                if duplicate_of:
                    movies_by_key[key] = duplicate_of
                    fallback_paths.setdefault(id(duplicate_of), relative)
                    duplicates_skipped += 1
                    processed += 1
                    if progress:
                        progress(relative, processed, "duplicate")
                    continue
                title, year = title_from_filename(path)
                movie = Movie(
                    title=title,
                    release_year=year,
                    relative_path=relative,
                    file_size=stat.st_size,
                    file_mtime_ns=stat.st_mtime_ns,
                    file_extension=path.suffix.lower(),
                    resolution=resolution_from_filename(path),
                )
                session.add(movie)
                movies_by_key[key] = movie
                movies_by_content[identity] = movie
                discovered += 1
                action = "added"
            else:
                if normalized_path_key(movie.relative_path) != key:
                    fallback_paths.setdefault(id(movie), relative)
                if not movie.resolution:
                    movie.resolution = resolution_from_filename(path)
                if movie.file_size != stat.st_size or movie.file_mtime_ns != stat.st_mtime_ns or not movie.is_available:
                    movie.file_size = stat.st_size
                    movie.file_mtime_ns = stat.st_mtime_ns
                    movie.is_available = True
                    movie.updated_at = datetime.now(timezone.utc)
                    session.add(movie)
                    updated += 1
                    action = "updated"
            processed += 1
            if progress:
                progress(relative, processed, action)
        except OSError:
            errors += 1

    # If the chosen copy disappeared but another identical copy remains, switch
    # the catalog record to that live path. Source files are never modified.
    unique_movies = list({id(movie): movie for movie in movies_by_key.values()}.values())
    for movie in unique_movies:
        if normalized_path_key(movie.relative_path) not in seen and id(movie) in fallback_paths:
            movie.relative_path = fallback_paths[id(movie)]
            session.add(movie)

    # Only reached after a complete successful traversal: preserve records, mark missing files unavailable.
    for movie in unique_movies:
        if normalized_path_key(movie.relative_path) not in seen and movie.is_available:
            movie.is_available = False
            movie.updated_at = datetime.now(timezone.utc)
            session.add(movie)
            updated += 1
    session.commit()
    return {"cancelled": False, "processed": processed, "discovered": discovered, "updated": updated, "duplicates_removed": duplicates_removed, "duplicates_skipped": duplicates_skipped, "errors": errors}

