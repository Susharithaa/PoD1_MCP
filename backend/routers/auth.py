from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse, UserResponse,
    UpdateRoleRequest, SetActiveRequest,
)
from utils.auth import hash_password, verify_password, create_access_token, get_current_user, require_admin
from utils.limiter import limiter
from config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_response(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        is_active=u.is_active,
        auth_provider=u.auth_provider,
        created_at=u.created_at.isoformat(),
    )


@router.post("/register", response_model=TokenResponse)
@limiter.limit("5/minute")
def register(request: Request, req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already registered")
    has_admin = db.query(User).filter(User.role == "admin").first() is not None
    bootstrap_emails = set(settings.admin_bootstrap_emails_list)
    should_be_admin = (not has_admin) or (req.email.strip().lower() in bootstrap_emails)
    user = User(
        id=str(uuid4()),
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role="admin" if should_be_admin else "user",
    )
    db.add(user)
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()

    if not user:
        raise HTTPException(401, "Invalid email or password")

    if user.auth_provider != "local":
        raise HTTPException(400, f"This account uses {user.auth_provider.title()} sign-in. "
                                 "Please use the social login button.")

    if not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")

    if not user.is_active:
        raise HTTPException(403, "Account is deactivated")

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return _user_response(current_user)


# ── Admin routes ──────────────────────────────────────────────────────────────

@router.get("/admin/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return [_user_response(u) for u in db.query(User).order_by(User.created_at).all()]


@router.patch("/admin/users/{user_id}/role", response_model=UserResponse)
def update_role(
    user_id: str,
    body: UpdateRoleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if body.role not in ("user", "admin"):
        raise HTTPException(400, "Role must be 'user' or 'admin'")
    if user_id == admin.id and body.role != "admin":
        raise HTTPException(400, "Cannot demote yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.role = body.role
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.patch("/admin/users/{user_id}/active", response_model=UserResponse)
def set_active(
    user_id: str,
    body: SetActiveRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(400, "Cannot deactivate yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return _user_response(user)
