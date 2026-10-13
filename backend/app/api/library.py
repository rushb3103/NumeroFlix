import threading
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, func, select

from app.core.config import Settings, get_settings
from app.core.database import engine, get_session
from app.models import Collection, Movie, WatchProgress
from app.services.scanner import scan_library

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

