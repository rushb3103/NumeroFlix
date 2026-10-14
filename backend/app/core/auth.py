import hashlib
import hmac
import secrets
import threading
from datetime import datetime, timedelta, timezone

from app.core.config import Settings

COOKIE_NAME = "numeroflix_session"
_sessions: dict[str, datetime] = {}
_lock = threading.Lock()


def authentication_required(settings: Settings) -> bool:
    return bool(settings.master_password)


def verify_password(candidate: str, settings: Settings) -> bool:
    expected = hashlib.sha256(settings.master_password.encode("utf-8")).digest()
    supplied = hashlib.sha256(candidate.encode("utf-8")).digest()
    return authentication_required(settings) and hmac.compare_digest(expected, supplied)


def create_session(settings: Settings) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_hours)
    with _lock:
        _remove_expired()
        _sessions[token] = expires_at
    return token, expires_at


def revoke_session(token: str | None) -> None:
    if not token:
        return
    with _lock:
        _sessions.pop(token, None)


def session_is_valid(token: str | None, settings: Settings) -> bool:
    if not authentication_required(settings):
        return True
    if not token:
        return False
    with _lock:
        _remove_expired()
        expires_at = _sessions.get(token)
        return bool(expires_at and expires_at > datetime.now(timezone.utc))


def _remove_expired() -> None:
    now = datetime.now(timezone.utc)
    for token, expiry in list(_sessions.items()):
        if expiry <= now:
            _sessions.pop(token, None)

