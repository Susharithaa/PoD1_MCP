"""
Agent flow routes:

  POST /api/agent/chat            start session from chat input
  POST /api/agent/upload          start session from uploaded doc
  GET  /api/agent/{id}            get session state
  POST /api/agent/{id}/hitl       submit human edits (HITL_PENDING → VALIDATING)
  POST /api/agent/{id}/confirm    confirm + save (alias for hitl with empty edits)
  GET  /api/agent/                list recent sessions
"""

import os
import uuid
import aiofiles
from fastapi import APIRouter, Body, Depends, HTTPException, Request, UploadFile, File
from typing import Any
from sqlalchemy.orm import Session

from database import get_db
from agents.orchestrator import AgentOrchestrator
from schemas.agent import (
    StartChatRequest,
    HITLSubmitRequest,
    ManualApiRequest,
    SessionResponse,
)
from config import settings
from utils.auth import get_current_user
from utils.encryption import encrypt_creds
from utils.limiter import limiter
from models.user import User

router = APIRouter(prefix="/api/agent", tags=["agent"])


def _orchestrator(db: Session = Depends(get_db)) -> AgentOrchestrator:
    return AgentOrchestrator(db=db)


def _get_session_or_404(session_id: str, db: Session, user_id: str | None = None):
    from models.agent_session import AgentSession
    session = db.get(AgentSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if user_id is not None and session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ---------------------------------------------------------------------------
# Start: Manual structured form (no LLM — auto-confirms after validation)
# ---------------------------------------------------------------------------
@router.post("/manual", response_model=SessionResponse, status_code=201)
@limiter.limit("30/minute")
async def create_manual(
    request: Request,
    req: ManualApiRequest,
    orch: AgentOrchestrator = Depends(_orchestrator),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Build an API definition from a structured form; validate + save immediately."""
    import uuid as _uuid
    from models.agent_session import AgentSession

    draft = {
        "name": req.name,
        "description": req.description,
        "base_url": req.base_url,
        "version": req.version,
        "auth_type": req.auth_type,
        "endpoints": [
            {
                "name": ep.name or f"{ep.method.upper()} {ep.path}",
                "description": ep.description,
                "method": ep.method.upper(),
                "path": ep.path,
                "auth_type": ep.auth_type or req.auth_type,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        p.name: {"type": p.type, "description": p.description}
                        for p in ep.parameters
                    },
                    "required": [p.name for p in ep.parameters if p.required],
                } if ep.parameters else {"type": "object", "properties": {}},
            }
            for ep in req.endpoints
        ],
    }

    confidence: dict = {
        "name":        {"status": "HIGH"},
        "base_url":    {"status": "HIGH"},
        "description": {"status": "HIGH" if req.description else "MISSING"},
    }
    for i, ep in enumerate(draft["endpoints"]):
        for key in ("name", "method", "path"):
            confidence[f"endpoints.{i}.{key}"] = {"status": "HIGH"}

    session = AgentSession(
        id=str(_uuid.uuid4()),
        mode="MANUAL",
        state="HITL_PENDING",
        raw_input=f"Manual form: {req.name}",
        draft_api=draft,
        confidence_map=confidence,
        auth_credentials=encrypt_creds(req.auth_credentials),
        user_id=current_user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Skip the LLM review step — go straight to validation + save.
    # Manual submissions are explicit, so don't block on unreachable test verdicts.
    session = await orch.confirm(session, {}, save_anyway=True)
    return session


# ---------------------------------------------------------------------------
# Start: Chat mode
# ---------------------------------------------------------------------------
@router.post("/chat", response_model=SessionResponse, status_code=201)
@limiter.limit("60/minute")
async def start_chat(
    request: Request,
    body: StartChatRequest,
    orch: AgentOrchestrator = Depends(_orchestrator),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start an agent session from a natural-language chat message."""
    session = await orch.start(raw_input=body.message)
    # Attach user_id after session is created
    session.user_id = current_user.id
    db.add(session)
    db.commit()
    return session


# ---------------------------------------------------------------------------
# Start: Document upload mode
# ---------------------------------------------------------------------------
@router.post("/upload", response_model=SessionResponse, status_code=201)
@limiter.limit("10/minute")
async def start_upload(
    request: Request,
    file: UploadFile = File(...),
    orch: AgentOrchestrator = Depends(_orchestrator),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start an agent session from an uploaded document."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "upload")[1]
    saved_path = os.path.join(settings.upload_dir, f"{uuid.uuid4()}{ext}")

    async with aiofiles.open(saved_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    session = await orch.start(file_path=saved_path)
    # Attach user_id after session is created
    session.user_id = current_user.id
    db.add(session)
    db.commit()
    return session


# ---------------------------------------------------------------------------
# Get session state
# ---------------------------------------------------------------------------
@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_session_or_404(session_id, db, user_id=current_user.id)


# ---------------------------------------------------------------------------
# HITL: submit human edits
# ---------------------------------------------------------------------------
@router.patch("/{session_id}/draft", response_model=SessionResponse)
def patch_draft(
    session_id: str,
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Persist partial draft_api edits without triggering the pipeline.
    Used by the HITL UI to immediately save endpoint deletions so they
    survive a page refresh.
    Only allowed while the session is in HITL_PENDING or FAILED state.
    """
    session = _get_session_or_404(session_id, db, user_id=current_user.id)
    if session.state not in ("HITL_PENDING", "FAILED"):
        raise HTTPException(400, "Session is not in an editable state")
    session.draft_api = {**(session.draft_api or {}), **body}
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/hitl", response_model=SessionResponse)
async def submit_hitl(
    session_id: str,
    body: HITLSubmitRequest,
    db: Session = Depends(get_db),
    orch: AgentOrchestrator = Depends(_orchestrator),
    current_user: User = Depends(get_current_user),
):
    """
    Submit human edits for a HITL_PENDING session.
    Triggers validation → save. Returns to HITL_PENDING if validation fails.
    """
    session = _get_session_or_404(session_id, db, user_id=current_user.id)
    if body.auth_credentials:
        session.auth_credentials = encrypt_creds(body.auth_credentials)
        db.add(session)
        db.commit()
    try:
        session = await orch.confirm(session, body.edits, save_anyway=body.save_anyway)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return session


# ---------------------------------------------------------------------------
# Confirm: save with no edits (shortcut)
# ---------------------------------------------------------------------------
@router.post("/{session_id}/confirm", response_model=SessionResponse)
async def confirm_session(
    session_id: str,
    db: Session = Depends(get_db),
    orch: AgentOrchestrator = Depends(_orchestrator),
    current_user: User = Depends(get_current_user),
):
    """Confirm a HITL_PENDING session with no edits."""
    session = _get_session_or_404(session_id, db, user_id=current_user.id)
    session = await orch.confirm(session, {})
    return session


# ---------------------------------------------------------------------------
# Discard session
# ---------------------------------------------------------------------------
@router.post("/{session_id}/discard", response_model=SessionResponse)
async def discard_session(
    session_id: str,
    db: Session = Depends(get_db),
    orch: AgentOrchestrator = Depends(_orchestrator),
    current_user: User = Depends(get_current_user),
):
    """Mark a HITL_PENDING or FAILED session as discarded."""
    session = _get_session_or_404(session_id, db, user_id=current_user.id)
    session = await orch.discard(session)
    return session


# ---------------------------------------------------------------------------
# Restart pipeline
# ---------------------------------------------------------------------------
@router.post("/{session_id}/restart", response_model=SessionResponse)
async def restart_session(
    session_id: str,
    db: Session = Depends(get_db),
    orch: AgentOrchestrator = Depends(_orchestrator),
    current_user: User = Depends(get_current_user),
):
    """
    Discard the current session and re-run the full pipeline with the same source.
    Returns the new session (starts from CLASSIFYING, ends at HITL_PENDING).
    """
    session = _get_session_or_404(session_id, db, user_id=current_user.id)
    new_session = await orch.restart(session)
    new_session.user_id = current_user.id
    db.add(new_session)
    db.commit()
    return new_session


# ---------------------------------------------------------------------------
# List sessions
# ---------------------------------------------------------------------------
@router.get("/", response_model=list[SessionResponse])
def list_sessions(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from models.agent_session import AgentSession
    from sqlalchemy import desc
    return (
        db.query(AgentSession)
        .filter(AgentSession.user_id == current_user.id)
        .order_by(desc(AgentSession.created_at))
        .limit(limit)
        .all()
    )
