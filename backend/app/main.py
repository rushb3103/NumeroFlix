import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.auth import COOKIE_NAME, session_is_valid
from app.core.config import get_settings
from app.core.database import create_db_and_tables

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.artwork_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    create_db_and_tables()
    yield


app = FastAPI(title="NumeroFlix API", version="0.1.0", lifespan=lifespan)

@app.middleware("http")
async def require_master_password(request: Request, call_next):
    path = request.url.path
    protected = path.startswith("/api/") or path.startswith("/artwork/")
    public_auth = path.startswith("/api/auth/") or path == "/api/auth"
    if request.method != "OPTIONS" and protected and not public_auth:
        if not session_is_valid(request.cookies.get(COOKIE_NAME), settings):
            return JSONResponse(status_code=401, content={"detail": "Master password required"})
    return await call_next(request)


# Register CORS last so it remains the outer middleware and also annotates 401 responses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


settings.artwork_dir.mkdir(parents=True, exist_ok=True)
app.mount("/artwork", StaticFiles(directory=settings.artwork_dir), name="artwork")


if settings.frontend_dir and settings.frontend_dir.is_dir():
    frontend_dir = settings.frontend_dir.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def serve_frontend(path: str) -> FileResponse:
        """Serve built SPA assets and fall back to index.html for client routes."""
        requested = (frontend_dir / path).resolve()
        if requested.is_relative_to(frontend_dir) and requested.is_file():
            return FileResponse(requested)
        return FileResponse(frontend_dir / "index.html")

