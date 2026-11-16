import json
import threading
import time
from uuid import UUID, uuid4
from pathlib import Path

from fastapi import Body, File, UploadFile
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, func, select

from app.core.config import Settings, get_settings
from app.core.database import engine, get_session
from app.models import Collection, Movie, WatchProgress
from app.services.paths import safe_movie_path
from app.services.scanner import SUPPORTED_EXTENSIONS, resolution_from_filename, scan_library, title_from_filename

router = APIRouter(prefix="/library", tags=["library"])

_lock = threading.Lock()
_cancel = threading.Event()
_state: dict = {
    "status": "idle",
    "phase": "idle",
    "current_file": None,
    "processed": 0,
    "events": [],
    "started_at": None,
    "finished_at": None,
    "result": None,
    "error": None,
}


def _run_scan(settings: Settings) -> None:
    from sqlmodel import Session

    def report(relative_path: str, processed: int, action: str) -> None:
        events = [*_state.get("events", []), {"file": relative_path, "action": action, "processed": processed}]
        _state.update(current_file=relative_path, processed=processed, phase="discovering", events=events[-60:])

    try:
        with Session(engine) as session:
            result = scan_library(session, settings.movie_root, _cancel, report)
        _state.update(
            status="cancelled" if result["cancelled"] else "complete",
            phase="cancelled" if result["cancelled"] else "complete",
            result=result,
        )
    except Exception as exc:  # state is intentionally user-visible; server log captures traceback
        _state.update(status="failed", phase="failed", error=str(exc))
    finally:
        _state.update(finished_at=datetime.now(timezone.utc).isoformat(), current_file=None)
        _lock.release()


@router.post("/scan", status_code=202)
def start_scan(background: BackgroundTasks, settings: Settings = Depends(get_settings)) -> dict:
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A library scan is already running")
    _cancel.clear()
    _state.update(
        status="running",
        phase="discovering",
        current_file=None,
        processed=0,
        events=[],
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
        result=None,
        error=None,
    )
    background.add_task(_run_scan, settings)
    return dict(_state)


@router.post("/scan/cancel", status_code=202)
def cancel_scan() -> dict:
    if _state["status"] != "running":
        raise HTTPException(status_code=409, detail="No scan is running")
    _cancel.set()
    return {"status": "cancelling"}


@router.get("/status")
def library_status(
    session: Session = Depends(get_session), settings: Settings = Depends(get_settings)
) -> dict:
    root_available = settings.movie_root.exists() and settings.movie_root.is_dir()
    total = session.exec(select(func.count(Movie.id))).one()
    available = session.exec(select(func.count(Movie.id)).where(Movie.is_available == True)).one()  # noqa: E712
    favorites = session.exec(select(func.count(Movie.id)).where(Movie.is_favorite == True)).one()  # noqa: E712
    collections = session.exec(select(func.count(Collection.id))).one()
    return {
        "root_available": root_available,
        "movie_root": str(settings.movie_root),
        "scan": dict(_state),
        "statistics": {"total": total, "available": available, "favorites": favorites, "collections": collections},
    }


@router.get("/dashboard")
def dashboard(session: Session = Depends(get_session)) -> dict:
    recent = session.exec(select(Movie).order_by(Movie.created_at.desc()).limit(12)).all()
    favorites = session.exec(select(Movie).where(Movie.is_favorite == True).order_by(Movie.updated_at.desc()).limit(12)).all()  # noqa: E712
    progress = session.exec(
        select(WatchProgress).where(WatchProgress.completed == False).order_by(WatchProgress.last_watched_at.desc()).limit(12)  # noqa: E712
    ).all()
    compact = lambda movie: {
        "id": movie.id,
        "title": movie.title,
        "release_year": movie.release_year,
        "poster_path": movie.poster_path,
        "backdrop_path": movie.backdrop_path,
        "duration_seconds": movie.duration_seconds,
        "file_size": movie.file_size,
        "resolution": movie.resolution,
        "is_available": movie.is_available,
    }
    return {
        "recent": [compact(item) for item in recent],
        "favorites": [compact(item) for item in favorites],
        "continue_watching": [{**compact(item.movie), "position_seconds": item.position_seconds} for item in progress],
    }



@router.post("/videos", status_code=201)
def upload_video(
    video: UploadFile = File(...),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    # Reject paths and platform-specific separators rather than trusting the client filename.
    name = video.filename or ""
    if not name or name in {".", ".."} or "/" in name or "\\" in name or ":" in name or any(ord(c) < 32 for c in name):
        raise HTTPException(status_code=400, detail="Invalid video filename")
    path_name = Path(name)
    if path_name.suffix.lower() not in SUPPORTED_EXTENSIONS or len(name) > 255:
        raise HTTPException(status_code=415, detail="Choose an MP4, MKV, AVI, MOV, WebM, or M4V video")
    root = settings.movie_root
    if not root.is_dir():
        raise HTTPException(status_code=503, detail="Library storage is unavailable")
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Wait for the current library operation to finish")
    destination = root / name
    created = False
    try:
        existing = session.exec(select(Movie).where(func.lower(Movie.relative_path) == name.lower())).first()
        if existing:
            raise HTTPException(status_code=409, detail="A video with that filename is already in the catalog")
        # Exclusive creation prevents overwriting a file, including a symlink.
        with destination.open("xb") as output:
            created = True
            while chunk := video.file.read(1024 * 1024):
                output.write(chunk)
        stat = destination.stat()
        title, year = title_from_filename(path_name)
        movie = Movie(title=title or path_name.stem, release_year=year, relative_path=name,
                      file_size=stat.st_size, file_mtime_ns=stat.st_mtime_ns,
                      file_extension=path_name.suffix.lower(), resolution=resolution_from_filename(path_name))
        session.add(movie)
        session.commit()
        session.refresh(movie)
        return {"id": movie.id, "title": movie.title}
    except HTTPException:
        raise
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail="A file with that name already exists in the library root") from exc
    except Exception as exc:
        session.rollback()
        if created:
            destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not save the video. Check library permissions and available space.") from exc
    finally:
        video.file.close()
        _lock.release()


@router.delete("/videos/{movie_id}", status_code=204)
def delete_video(movie_id: int, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Wait for the current library operation to finish")
    try:
        movie = session.get(Movie, movie_id)
        if not movie:
            raise HTTPException(status_code=404, detail="Video not found")
        try:
            path = safe_movie_path(settings.movie_root, movie.relative_path)
            path.unlink()
        except OSError as exc:
            raise HTTPException(status_code=503, detail="Could not delete the file. Check library storage and permissions.") from exc
        try:
            session.delete(movie)
            session.commit()
        except Exception as exc:
            session.rollback()
            raise HTTPException(status_code=500, detail="The file was deleted, but its catalog entry could not be removed. Run a scan.") from exc
    finally:
        _lock.release()


# Chunks are staged outside the movie root so scans never index incomplete files.
CHUNK_SIZE = 8 * 1024 * 1024
UPLOAD_TTL = 24 * 60 * 60
_upload_lock = threading.Lock()


class UploadStart(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    size: int = Field(gt=0)


def _upload_paths(settings: Settings, upload_id: UUID) -> tuple[Path, Path]:
    directory = settings.cache_dir / "uploads"
    return directory / f"{upload_id}.json", directory / f"{upload_id}.part"


def _upload_info(settings: Settings, upload_id: UUID) -> tuple[dict, Path, Path]:
    meta, data = _upload_paths(settings, upload_id)
    try:
        info = json.loads(meta.read_text(encoding="utf-8"))
        if not data.is_file():
            raise FileNotFoundError
        return info, meta, data
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Upload not found or expired") from exc


@router.post("/uploads", status_code=201)
def start_upload(payload: UploadStart, settings: Settings = Depends(get_settings)) -> dict:
    name = payload.filename
    if name in {".", ".."} or "/" in name or "\\" in name or ":" in name or any(ord(c) < 32 for c in name):
        raise HTTPException(status_code=400, detail="Invalid video filename")
    if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Choose an MP4, MKV, AVI, MOV, WebM, or M4V video")
    if not settings.movie_root.is_dir():
        raise HTTPException(status_code=503, detail="Library storage is unavailable")
    upload_id = uuid4()
    meta, data = _upload_paths(settings, upload_id)
    with _upload_lock:
        meta.parent.mkdir(parents=True, exist_ok=True)
        # Remove abandoned staging files on a later visit; active uploads touch the metadata.
        for old in meta.parent.glob("*.json"):
            try:
                if time.time() - old.stat().st_mtime > UPLOAD_TTL:
                    old.with_suffix(".part").unlink(missing_ok=True)
                    old.unlink(missing_ok=True)
            except OSError:
                continue
        try:
            data.touch(exist_ok=False)
            meta.write_text(json.dumps(payload.model_dump()), encoding="utf-8")
        except OSError as exc:
            data.unlink(missing_ok=True)
            raise HTTPException(status_code=503, detail="Could not prepare upload storage") from exc
    return {"id": str(upload_id), "chunk_size": CHUNK_SIZE}


@router.put("/uploads/{upload_id}")
def upload_chunk(upload_id: UUID, offset: int, chunk: bytes = Body(media_type="application/octet-stream"), settings: Settings = Depends(get_settings)) -> dict:
    with _upload_lock:
        info, meta, data = _upload_info(settings, upload_id)
        current = data.stat().st_size
        if offset != current:
            raise HTTPException(status_code=409, detail=f"Expected upload offset {current}")
        if not chunk or len(chunk) > CHUNK_SIZE or current + len(chunk) > info["size"]:
            raise HTTPException(status_code=400, detail="Invalid upload chunk size")
        try:
            with data.open("ab") as output:
                output.write(chunk)
            meta.touch()
        except OSError as exc:
            raise HTTPException(status_code=507, detail="Could not store upload chunk; check disk space") from exc
        return {"received": current + len(chunk)}


@router.post("/uploads/{upload_id}/complete", status_code=201)
def complete_upload(upload_id: UUID, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)) -> dict:
    with _upload_lock:
        info, meta, data = _upload_info(settings, upload_id)
        if data.stat().st_size != info["size"]:
            raise HTTPException(status_code=409, detail="Upload is incomplete")
        # Existing upload logic performs exclusive creation and indexes the finished file.
        with data.open("rb") as source:
            result = upload_video(UploadFile(filename=info["filename"], file=source), session, settings)
        data.unlink(missing_ok=True)
        meta.unlink(missing_ok=True)
        return result


@router.delete("/uploads/{upload_id}", status_code=204)
def cancel_upload(upload_id: UUID, settings: Settings = Depends(get_settings)):
    with _upload_lock:
        meta, data = _upload_paths(settings, upload_id)
        data.unlink(missing_ok=True)
        meta.unlink(missing_ok=True)
