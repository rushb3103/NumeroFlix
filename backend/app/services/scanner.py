import re
import stat
import threading
from collections.abc import Iterator
from datetime import datetime, timezone
from os import stat_result
from os.path import samestat
from pathlib import Path

from sqlmodel import Session, select

from app.models import Movie, WatchProgress
from app.services.media import first_frame_resolution

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


def _movie_paths(root: Path, cancel: threading.Event | None) -> Iterator[Path]:
    def raise_walk_error(error: OSError) -> None:
        raise error

    for directory, subdirectories, filenames in root.walk(on_error=raise_walk_error):
        if cancel and cancel.is_set():
            return
        subdirectories[:] = [name for name in subdirectories if not (directory / name).is_junction()]
        for name in filenames:
            path = directory / name
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield path


def scan_library(
    session: Session, root: Path, cancel: threading.Event | None = None, progress=None, *, ffmpeg_path: str = "ffmpeg"
) -> dict:
    root_stat = root.stat()
    if not stat.S_ISDIR(root_stat.st_mode):
        raise FileNotFoundError(f"Movie root is unavailable: {root}")

    discovered = updated = removed = errors = processed = duplicates_removed = duplicates_skipped = 0
    resolution_unavailable = 0

    def result(cancelled: bool) -> dict:
        return {
            "cancelled": cancelled, "processed": processed, "discovered": discovered, "updated": updated,
            "removed": removed, "duplicates_removed": duplicates_removed, "duplicates_skipped": duplicates_skipped,
            "errors": errors, "resolution_unavailable": resolution_unavailable,
        }

    files: list[tuple[Path, str, stat_result]] = []
    for path in _movie_paths(root, cancel):
        if cancel and cancel.is_set():
            return result(True)
        try:
            file_stat = path.lstat()
        except FileNotFoundError:
            errors += 1
            continue
        if stat.S_ISREG(file_stat.st_mode):
            files.append((path, path.relative_to(root).as_posix(), file_stat))
    if cancel and cancel.is_set():
        return result(True)

    movies_by_key: dict[str, Movie] = {}
    movies_by_content: dict[tuple[str, int, int], Movie] = {}
    catalog: list[Movie] = []
    for existing in session.exec(select(Movie).order_by(Movie.id)).all():
        key = normalized_path_key(existing.relative_path)
        identity = content_identity(existing.relative_path, existing.file_size, existing.file_mtime_ns)
        canonical = movies_by_key.get(key) or movies_by_content.get(identity)
        if canonical:
            _merge_duplicate(session, canonical, existing)
            duplicates_removed += 1
            movies_by_key[key] = canonical
        else:
            catalog.append(existing)
            movies_by_key[key] = existing
            movies_by_content[identity] = existing
    if duplicates_removed:
        session.flush()

    # Refresh known paths before matching copies by their stored size and mtime.
    known_paths = {movie.relative_path for movie in catalog}
    files.sort(key=lambda entry: (entry[1] not in known_paths, normalized_path_key(entry[1]) not in movies_by_key))
    matched: set[int] = set()
    for path, relative, file_stat in files:
        if cancel and cancel.is_set():
            session.rollback()
            return result(True)
        key = normalized_path_key(relative)
        identity = content_identity(relative, file_stat.st_size, file_stat.st_mtime_ns)
        movie = movies_by_key.get(key)
        if movie is None or normalized_path_key(movie.relative_path) != key:
            movie = movies_by_content.get(identity)
        action = "checked"
        if movie is None:
            title, year = title_from_filename(path)
            movie = Movie(
                title=title,
                release_year=year,
                relative_path=relative,
                file_size=file_stat.st_size,
                file_mtime_ns=file_stat.st_mtime_ns,
                file_extension=path.suffix.lower(),
                resolution=resolution_from_filename(path),
                first_frame_resolution=first_frame_resolution(path, ffmpeg_path),
            )
            session.add(movie)
            movies_by_key[key] = movie
            movies_by_content[identity] = movie
            discovered += 1
            action = "added"
        elif id(movie) in matched:
            duplicates_skipped += 1
            action = "duplicate"
        else:
            previous_identity = content_identity(movie.relative_path, movie.file_size, movie.file_mtime_ns)
            changed = previous_identity != identity
            if changed:
                if movies_by_content.get(previous_identity) is movie:
                    del movies_by_content[previous_identity]
                movies_by_content[identity] = movie
                movie.file_size = file_stat.st_size
                movie.file_mtime_ns = file_stat.st_mtime_ns
                movie.resolution = resolution_from_filename(path)
                movie.duration_seconds = movie.video_codec = movie.audio_codec = None
            dimensions = movie.first_frame_resolution
            if changed or dimensions is None:
                dimensions = first_frame_resolution(path, ffmpeg_path)
            if (
                changed or relative != movie.relative_path
                or dimensions != movie.first_frame_resolution or not movie.is_available
            ):
                # An identical live copy can take over the entry and its assignments.
                movie.relative_path = relative
                movies_by_key[key] = movie
                movie.first_frame_resolution = dimensions
                movie.is_available = True
                movie.updated_at = datetime.now(timezone.utc)
                updated += 1
                action = "updated"
        if action != "duplicate":
            matched.add(id(movie))
            if movie.first_frame_resolution is None:
                resolution_unavailable += 1
        processed += 1
        if progress:
            progress(relative, processed, action)

    if cancel and cancel.is_set():
        session.rollback()
        return result(True)
    for movie in catalog:
        if id(movie) not in matched:
            session.delete(movie)
            removed += 1

    if cancel and cancel.is_set():
        session.rollback()
        return result(True)
    if not samestat(root_stat, root.stat()):
        session.rollback()
        raise OSError(f"Movie root changed during the scan: {root}")
    session.commit()
    return result(False)

