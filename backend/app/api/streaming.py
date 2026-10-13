import mimetypes
import re
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.models import Movie
from app.services.paths import safe_movie_path

router = APIRouter(prefix="/movies", tags=["streaming"])
CHUNK_SIZE = 1024 * 1024


def parse_range(value: str | None, size: int) -> tuple[int, int] | None:
    if not value:
        return None
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", value.strip())
    if not match or "," in value:
        raise HTTPException(status_code=416, detail="Invalid or unsupported byte range", headers={"Content-Range": f"bytes */{size}"})
    first, last = match.groups()
    if not first and not last:
        raise HTTPException(status_code=416, detail="Invalid byte range", headers={"Content-Range": f"bytes */{size}"})
    if not first:  # suffix range
        length = int(last)
        if length <= 0:
            raise HTTPException(status_code=416, detail="Invalid byte range", headers={"Content-Range": f"bytes */{size}"})
        start, end = max(size - length, 0), size - 1
    else:
        start = int(first)
        end = int(last) if last else size - 1
    if start >= size or start < 0 or end < start:
        raise HTTPException(status_code=416, detail="Range not satisfiable", headers={"Content-Range": f"bytes */{size}"})
    return start, min(end, size - 1)


def read_chunks(path: Path, start: int, length: int) -> Iterator[bytes]:
    remaining = length
    with path.open("rb") as stream:
        stream.seek(start)
        while remaining > 0:
            chunk = stream.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def resolve(movie_id: int, session: Session, settings: Settings) -> tuple[Movie, Path]:
    movie = session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    if not movie.is_available:
        raise HTTPException(status_code=404, detail="Movie is currently unavailable")
    try:
        return movie, safe_movie_path(settings.movie_root, movie.relative_path)
    except (FileNotFoundError, OSError):
        raise HTTPException(status_code=503, detail="Movie storage is unavailable") from None


@router.api_route("/{movie_id}/stream", methods=["GET", "HEAD"])
def stream_movie(
    movie_id: int,
    request: Request,
    range_header: str | None = Header(default=None, alias="Range"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    movie, path = resolve(movie_id, session, settings)
    size = path.stat().st_size
    byte_range = parse_range(range_header, size)
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    headers = {"Accept-Ranges": "bytes", "Cache-Control": "private, no-store"}
    if byte_range:
        start, end = byte_range
        length = end - start + 1
        headers.update({"Content-Range": f"bytes {start}-{end}/{size}", "Content-Length": str(length)})
        if request.method == "HEAD":
            return Response(status_code=206, media_type=mime, headers=headers)
        return StreamingResponse(read_chunks(path, start, length), status_code=206, media_type=mime, headers=headers)
    headers["Content-Length"] = str(size)
    if request.method == "HEAD":
        return Response(status_code=200, media_type=mime, headers=headers)
    return StreamingResponse(read_chunks(path, 0, size), media_type=mime, headers=headers)

