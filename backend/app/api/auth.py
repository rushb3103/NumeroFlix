from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.auth import COOKIE_NAME, create_session, revoke_session, session_is_valid, verify_password
from app.core.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


@router.get("/status")
def auth_status(request: Request, settings: Settings = Depends(get_settings)) -> dict[str, bool]:
    required = bool(settings.master_password)
    return {
        "required": required,
        "authenticated": session_is_valid(request.cookies.get(COOKIE_NAME), settings),
    }


@router.post("/login")
def login(payload: LoginRequest, response: Response, settings: Settings = Depends(get_settings)) -> dict[str, bool]:
    if not settings.master_password:
        return {"authenticated": True}
    if not verify_password(payload.password, settings):
        raise HTTPException(status_code=401, detail="Incorrect master password")
    token, expires_at = create_session(settings)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.session_hours * 60 * 60,
        expires=expires_at,
        httponly=True,
        secure=settings.app_env.lower() == "production",
        samesite="strict",
        path="/",
    )
    return {"authenticated": True}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    revoke_session(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"authenticated": False}

