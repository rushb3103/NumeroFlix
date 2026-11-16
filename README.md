# NumeroFlix

NumeroFlix is a private, local movie catalog for a decrypted Cryptomator filesystem. It indexes filenames and metadata into its own database, organizes movies with tags and collections, and streams browser-compatible media. Admins can also upload and delete source videos.

The earlier Flask prototype remains at the repository root for reference. The active MVP lives in `backend/` and `frontend/`.

## Implemented

- FastAPI, SQLModel, SQLite, Alembic-compatible schema, and health endpoint
- Incremental, cancellable, read-only recursive scanning for MP4, MKV, AVI, MOV, WebM, and M4V
- Disconnected-storage handling; scans retain records and only mark missing entries unavailable after a complete scan
- Paginated search, multi-tag/year/genre/watched/favorite filters, and sorting
- Tag CRUD/bulk assignment, collection CRUD/membership, favorites, watched state, and playback progress
- Optional master-password gate using an HttpOnly expiring session cookie
- Secure movie-ID-based streaming with GET/HEAD, byte ranges, seeking headers, path containment, and symlink rejection
- Lazy ffprobe inspection, optional TMDB search, and local custom poster uploads
- Responsive React/Vite/Tailwind UI with dashboard, library, details, collections, player, and settings
- Scanner, API, path safety, range streaming, CRUD, search, and progress tests

## Local setup (Windows 11)

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 20+, npm, and optionally FFmpeg/ffprobe.

1. Copy `.env.example` to `backend/.env`, set `MOVIE_ROOT` to the unlocked, decrypted movie drive, and set `MASTER_PASSWORD`. Use forward slashes for Windows paths (for example `Z:/Movies`). Leave `MASTER_PASSWORD` empty only if you intentionally want to disable the login gate.
2. Install and run the API:

   ```powershell
   cd backend
   uv sync
   uv run alembic upgrade head
   uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. In another terminal, install and run the UI:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Open `http://localhost:5173`. The API docs are at `http://127.0.0.1:8000/docs`.

After dependencies are installed, `scripts/start-dev.ps1` and `scripts/stop-dev.ps1` start/stop both services in the background.

## Docker Compose and Cloudflare Tunnel

The container image builds the React UI and serves it from the FastAPI process on port 8000. Compose mounts the movie library read-write for admin uploads and deletion, keeps the database/artwork/cache in a named volume, and runs a remotely managed Cloudflare Tunnel alongside the app.

1. In Cloudflare Zero Trust, create a remotely managed tunnel and add a public hostname whose service URL is `http://numeroflix:8000`.
2. Copy `.env.compose.example` to `.env.compose`. Set `MOVIE_PATH`, `MASTER_PASSWORD`, and the tunnel token from Cloudflare. Keep this file private.
3. Build and start the stack:

   ```powershell
   docker compose --env-file .env.compose up -d --build
   ```

4. Check the services with `docker compose --env-file .env.compose ps` and follow tunnel logs with `docker compose --env-file .env.compose logs -f cloudflared`.

The app is also available only on the Docker host at `http://127.0.0.1:8000` by default. Change `APP_PORT` if needed. Stop the stack with `docker compose --env-file .env.compose down`; the `numeroflix-data` volume is retained.

## Tests and build

```powershell
cd backend
uv run pytest
cd ../frontend
npm run build
```

Tests use temporary directories and dummy bytes; no B2, Cryptomator, TMDB, or real media is required.

## Storage safety

Scanning and streaming read files beneath `MOVIE_ROOT`. Admin uploads create files in the library root; admin deletion permanently removes the selected source file and catalog entry. File operations reject paths escaping the root and symlinked paths. The database, artwork, cache, and logs live under the backend data directory by default. The app needs write permission on the library for uploads and deletion.

## Current limitations / later phases

- Direct playback depends on browser container/codec support; HLS transcoding is not yet implemented.
- TMDB matching is manual and optional; automatic filename matching is intentionally not implemented.
- Multi-profile history, PostgreSQL deployment, and background workers are future deployment work.
- Browser subtitle track discovery and grid bulk-selection controls are not yet implemented; individual tag assignment and the backend bulk-tag endpoint are available.

## Admin mode and thumbnails

Turn on **Admin** in the header to scan the library, manage categories and tags, upload or delete videos, and edit a video from its watch page. Existing collections appear as categories. The switch changes the interface; it is not a separate security boundary. Configure the master password to restrict access.

After updating an existing installation, run `uv run alembic upgrade head` in `backend` before starting the API. FFmpeg and ffprobe must be installed and available on the server (or configured via `FFMPEG_PATH` and `FFPROBE_PATH`). The editor generates 20 evenly spaced frames on demand; thumbnail images are generated from the saved timestamp and are not stored.

Video uploads use 8 MiB chunks to work through Cloudflare request limits. Incomplete uploads are staged in `CACHE_DIR/uploads` and removed on failure or after 24 hours when a new upload starts. Allow local disk space for the staged video and the rclone VFS cache; rclone may continue transferring data to B2 after NumeroFlix reports that the video was added.
