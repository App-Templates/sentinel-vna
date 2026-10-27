"""Google OAuth authentication for Sentinel.

In development (ENVIRONMENT=development), auth is bypassed entirely.
In production, only @adkaora.com emails are allowed via Google OAuth.
"""

from __future__ import annotations

import os
import secrets
import time

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory session store (sufficient for team <20)
_sessions: dict[str, dict] = {}

oauth = OAuth()


def _is_dev() -> bool:
    return os.getenv("ENVIRONMENT", "development") == "development"


def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173")


def _allowed_domain() -> str:
    return os.getenv("ALLOWED_DOMAIN", "adkaora.com")


def setup_oauth() -> None:
    """Register Google OAuth client. Only effective when credentials are set."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if client_id and client_secret:
        oauth.register(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def require_auth(request: Request) -> dict:
    """Return current user dict or raise 401."""
    if _is_dev():
        return {"email": "stefano@hej.ia", "name": "Stefano", "picture": ""}

    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in _sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = _sessions[session_id]
    if time.time() - session.get("created_at", 0) > 86400:
        _sessions.pop(session_id, None)
        raise HTTPException(status_code=401, detail="Session expired")

    return session["user"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/login")
async def login(request: Request):
    if _is_dev():
        return RedirectResponse(url=_frontend_url())
    if not hasattr(oauth, "google") or oauth.google is None:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request):
    if _is_dev():
        return RedirectResponse(url=_frontend_url())

    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info from Google")

    email: str = user_info.get("email", "")
    domain = _allowed_domain()
    if not email.endswith(f"@{domain}"):
        raise HTTPException(status_code=403, detail=f"Only @{domain} emails are allowed")

    session_id = secrets.token_urlsafe(32)
    _sessions[session_id] = {
        "user": {
            "email": email,
            "name": user_info.get("name", ""),
            "picture": user_info.get("picture", ""),
        },
        "created_at": time.time(),
    }

    response = RedirectResponse(url=_frontend_url())
    is_prod = not _is_dev()
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=86400,
    )
    return response


@router.get("/me")
async def me(user: dict = Depends(require_auth)):
    return user


@router.post("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        _sessions.pop(session_id, None)
    resp = Response(content='{"ok": true}', media_type="application/json")
    resp.delete_cookie("session_id")
    return resp
