import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.operational import ApiToken
from models.user import User
from utils.auth import generate_api_token, get_current_user, hash_api_token
from utils.observability import emit_audit

router = APIRouter(prefix="/api/security", tags=["security"])


class TokenCreateRequest(BaseModel):
    name: str
    scopes: list[str] = ["tools:read"]


class TokenResponse(BaseModel):
    id: str
    name: str
    token_prefix: str
    scopes: list[str]
    created_at: str
    last_used_at: str | None = None
    revoked_at: str | None = None


def _token_response(row: ApiToken) -> TokenResponse:
    return TokenResponse(
        id=row.id,
        name=row.name,
        token_prefix=row.token_prefix,
        scopes=row.scopes or [],
        created_at=row.created_at.isoformat(),
        last_used_at=row.last_used_at.isoformat() if row.last_used_at else None,
        revoked_at=row.revoked_at.isoformat() if row.revoked_at else None,
    )


@router.get("/tokens", response_model=list[TokenResponse])
def list_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(ApiToken).filter(ApiToken.user_id == current_user.id).order_by(ApiToken.created_at.desc()).all()
    return [_token_response(row) for row in rows]


@router.post("/tokens", status_code=201)
def create_token(
    body: TokenCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    raw, prefix, hashed = generate_api_token()
    row = ApiToken(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=body.name,
        token_prefix=prefix,
        token_hash=hashed,
        scopes=body.scopes,
    )
    db.add(row)
    db.commit()
    emit_audit("api_token.created", user=current_user, resource_type="api_token", resource_id=row.id, request=request)
    payload = _token_response(row).model_dump()
    payload["token"] = raw
    return payload


@router.post("/tokens/{token_id}/rotate")
def rotate_token(
    token_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    row = db.query(ApiToken).filter(ApiToken.id == token_id, ApiToken.user_id == current_user.id).first()
    if not row:
        raise HTTPException(404, "Token not found")
    raw, prefix, hashed = generate_api_token()
    row.token_prefix = prefix
    row.token_hash = hashed
    row.revoked_at = None
    db.commit()
    db.refresh(row)
    emit_audit("api_token.rotated", user=current_user, resource_type="api_token", resource_id=row.id, request=request)
    payload = _token_response(row).model_dump()
    payload["token"] = raw
    return payload


@router.delete("/tokens/{token_id}", status_code=204)
def revoke_token(
    token_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(ApiToken).filter(ApiToken.id == token_id, ApiToken.user_id == current_user.id).first()
    if not row:
        raise HTTPException(404, "Token not found")
    row.revoked_at = datetime.now(timezone.utc)
    row.token_hash = hash_api_token(f"revoked:{row.id}:{row.revoked_at.isoformat()}")
    db.commit()
    emit_audit("api_token.revoked", user=current_user, resource_type="api_token", resource_id=row.id, request=request)
