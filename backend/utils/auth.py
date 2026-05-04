from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from config import settings
from database import get_db
from models.user import User
from models.operational import ApiToken

try:
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:  # pragma: no cover - fallback for stripped dev environments
    pwd_context = None
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    if pwd_context:
        return pwd_context.hash(password)
    return "sha256$" + hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    if pwd_context and hashed.startswith("$2"):
        return pwd_context.verify(plain, hashed)
    if hashed.startswith("sha256$"):
        return hashed == hash_password(plain)
    return False


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def hash_api_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_api_token() -> tuple[str, str, str]:
    raw = "mcp_" + secrets.token_urlsafe(32)
    return raw, raw[:12], hash_api_token(raw)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str | None = payload.get("sub")
        if user_id:
            user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    except JWTError:
        token_hash = hash_api_token(token)
        api_token = db.query(ApiToken).filter(
            ApiToken.token_hash == token_hash,
            ApiToken.revoked_at.is_(None),
        ).first()
        if api_token:
            api_token.last_used_at = datetime.now(timezone.utc)
            db.commit()
            user = db.query(User).filter(User.id == api_token.user_id, User.is_active == True).first()
            if user:
                setattr(user, "api_token_scopes", api_token.scopes or [])
    if not user:
        raise exc
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_scope(scope: str):
    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == "admin":
            return current_user
        scopes = set(getattr(current_user, "api_token_scopes", []) or [])
        if scope not in scopes and "*" not in scopes:
            raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")
        return current_user
    return _dependency
