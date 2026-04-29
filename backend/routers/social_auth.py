"""
Google and Microsoft OAuth2 sign-in.

Flow:
  1. Frontend opens  GET /api/auth/google          → redirects to Google consent screen
  2. Google redirects GET /api/auth/google/callback → exchanges code, finds/creates user
  3. Backend redirects to {FRONTEND_URL}/auth/callback?token=<jwt>
  4. Frontend AuthCallback page stores token, navigates to /
"""
from uuid import uuid4
import httpx
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.user import User
from utils.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["social-auth"])

_GOOGLE_AUTH_URL    = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL   = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO    = "https://www.googleapis.com/oauth2/v3/userinfo"

_GH_AUTH_URL        = "https://github.com/login/oauth/authorize"
_GH_TOKEN_URL       = "https://github.com/login/oauth/access_token"
_GH_USERINFO        = "https://api.github.com/user"
_GH_EMAILS          = "https://api.github.com/user/emails"


# ── Google ────────────────────────────────────────────────────────────────────

@router.get("/google")
def google_login():
    if not settings.google_client_id:
        raise HTTPException(501, "Google OAuth2 not configured (GOOGLE_CLIENT_ID missing)")
    params = {
        "client_id":     settings.google_client_id,
        "redirect_uri":  settings.google_redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "online",
    }
    return RedirectResponse(f"{_GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(code: str | None = None, error: str | None = None,
                    db: Session = Depends(get_db)):
    if error or not code:
        return RedirectResponse(f"{settings.frontend_url}/login?error=google_denied")

    try:
        token_data = _exchange_google_code(code)
        user_info  = _get_google_user(token_data["access_token"])
    except Exception as exc:
        return RedirectResponse(f"{settings.frontend_url}/login?error=google_failed")

    email      = user_info.get("email", "").lower()
    full_name  = user_info.get("name", "")
    if not email:
        return RedirectResponse(f"{settings.frontend_url}/login?error=no_email")

    user = _find_or_create(db, email, full_name, "google")
    jwt  = create_access_token(user.id)
    return RedirectResponse(f"{settings.frontend_url}/auth/callback?token={jwt}")


def _exchange_google_code(code: str) -> dict:
    resp = httpx.post(_GOOGLE_TOKEN_URL, data={
        "code":          code,
        "client_id":     settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri":  settings.google_redirect_uri,
        "grant_type":    "authorization_code",
    })
    resp.raise_for_status()
    return resp.json()


def _get_google_user(access_token: str) -> dict:
    resp = httpx.get(_GOOGLE_USERINFO,
                     headers={"Authorization": f"Bearer {access_token}"})
    resp.raise_for_status()
    return resp.json()


# ── GitHub ────────────────────────────────────────────────────────────────────

@router.get("/github")
def github_login():
    if not settings.github_client_id:
        raise HTTPException(501, "GitHub OAuth2 not configured (GITHUB_CLIENT_ID missing)")
    params = {
        "client_id":    settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope":        "user:email",
    }
    return RedirectResponse(f"{_GH_AUTH_URL}?{urlencode(params)}")


@router.get("/github/callback")
def github_callback(code: str | None = None, error: str | None = None,
                    db: Session = Depends(get_db)):
    if error or not code:
        return RedirectResponse(f"{settings.frontend_url}/login?error=github_denied")

    try:
        access_token = _exchange_github_code(code)
        user_info    = _get_github_user(access_token)
        email        = _get_github_email(access_token, user_info)
    except Exception:
        return RedirectResponse(f"{settings.frontend_url}/login?error=github_failed")

    if not email:
        return RedirectResponse(f"{settings.frontend_url}/login?error=no_email")

    full_name = user_info.get("name") or user_info.get("login", "")
    user = _find_or_create(db, email.lower(), full_name, "github")
    jwt  = create_access_token(user.id)
    return RedirectResponse(f"{settings.frontend_url}/auth/callback?token={jwt}")


def _exchange_github_code(code: str) -> str:
    resp = httpx.post(_GH_TOKEN_URL, data={
        "code":          code,
        "client_id":     settings.github_client_id,
        "client_secret": settings.github_client_secret,
        "redirect_uri":  settings.github_redirect_uri,
    }, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()["access_token"]


def _get_github_user(access_token: str) -> dict:
    resp = httpx.get(_GH_USERINFO, headers={
        "Authorization": f"Bearer {access_token}",
        "Accept":        "application/vnd.github+json",
    })
    resp.raise_for_status()
    return resp.json()


def _get_github_email(access_token: str, user_info: dict) -> str:
    if user_info.get("email"):
        return user_info["email"]
    resp = httpx.get(_GH_EMAILS, headers={
        "Authorization": f"Bearer {access_token}",
        "Accept":        "application/vnd.github+json",
    })
    resp.raise_for_status()
    primary = next((e["email"] for e in resp.json() if e.get("primary") and e.get("verified")), None)
    return primary or ""


# ── Shared helper ─────────────────────────────────────────────────────────────

def _find_or_create(db: Session, email: str, full_name: str, provider: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Link provider if user previously registered with password
        if user.auth_provider == "local":
            user.auth_provider = provider
            db.commit()
        return user

    is_first = db.query(User).count() == 0
    user = User(
        id=str(uuid4()),
        email=email,
        hashed_password=None,
        full_name=full_name,
        role="admin" if is_first else "user",
        auth_provider=provider,
    )
    db.add(user)
    db.commit()
    return user
