from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models.user import User
from models.token_usage import TokenUsage
from utils.auth import get_current_user, require_admin
from schemas.subscription import (
    SubscriptionStatusResponse, TopUpRequest, AccessRequestsResponse,
)

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


# ── User-facing ───────────────────────────────────────────────────────────────

@router.post("/request")
def request_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.chat_status == "approved":
        raise HTTPException(400, "You already have chat access")
    if current_user.chat_status == "pending":
        raise HTTPException(400, "Your request is already pending approval")

    current_user.chat_status = "pending"
    db.commit()
    return {"message": "Access request submitted. You'll be notified once approved."}


@router.get("/status", response_model=SubscriptionStatusResponse)
def get_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_spent = db.query(TokenUsage).filter(
        TokenUsage.user_id == current_user.id
    ).with_entities(
        __import__("sqlalchemy").func.sum(TokenUsage.cost_usd)
    ).scalar() or 0.0

    return SubscriptionStatusResponse(
        chat_status=current_user.chat_status,
        credits=round(current_user.credits, 6),
        total_spent=round(total_spent, 6),
    )


# ── Admin-facing ──────────────────────────────────────────────────────────────

@router.get("/admin/requests", response_model=list[AccessRequestsResponse])
def list_requests(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    users = db.query(User).filter(User.chat_status == "pending").all()
    return [
        AccessRequestsResponse(
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            chat_status=u.chat_status,
            credits=u.credits,
        )
        for u in users
    ]


@router.get("/admin/all-users", response_model=list[AccessRequestsResponse])
def list_all_chat_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    users = db.query(User).filter(User.chat_status != "none").all()
    return [
        AccessRequestsResponse(
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            chat_status=u.chat_status,
            credits=u.credits,
        )
        for u in users
    ]


@router.patch("/admin/{user_id}/approve")
def approve_access(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.chat_status = "approved"
    db.commit()
    return {"message": f"Chat access approved for {user.email}"}


@router.patch("/admin/{user_id}/reject")
def reject_access(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.chat_status = "rejected"
    db.commit()
    return {"message": f"Chat access rejected for {user.email}"}


@router.post("/admin/{user_id}/top-up")
def top_up_credits(
    user_id: str,
    body: TopUpRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if body.amount <= 0:
        raise HTTPException(400, "Amount must be greater than 0")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.chat_status != "approved":
        raise HTTPException(400, "User does not have approved chat access")
    user.credits = round(user.credits + body.amount, 6)
    db.commit()
    return {"message": f"Added ${body.amount:.2f} credits to {user.email}", "new_balance": user.credits}
