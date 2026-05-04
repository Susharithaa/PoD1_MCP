from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models.agent_session import AgentSession
from models.api_definition import ApiDefinition
from models.chatgpt_connection import ChatGPTConnection, ToolCallLog
from models.chat_audit import ChatAuditLog
from utils.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/api/monitor", tags=["monitor"])

ACTIVE_STATES = {
    "CLASSIFYING", "PARSING", "SCHEMA_GENERATING", "CONFIDENCE_SCORING",
    "VALIDATING", "API_TESTING", "SAVING",
}


def _now():
    return datetime.now(timezone.utc)


def _api_name(session: AgentSession) -> str:
    for src in (session.final_api, session.draft_api):
        name = (src or {}).get("name")
        if name:
            return name
    return "—"


def _test_summary(results) -> str:
    if not results:
        return "NONE"
    verdicts = [r.get("verdict", "SKIPPED") for r in results]
    if "UNREACHABLE" in verdicts:
        return "UNREACHABLE"
    if "WARNING" in verdicts:
        return "WARNING"
    if all(v in ("PASS", "SKIPPED", "AUTH_REQUIRED") for v in verdicts):
        return "PASS"
    return "UNKNOWN"


def _elapsed(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, int((_now() - dt).total_seconds()))


def _visible_sessions_query(db: Session, current_user: User):
    query = db.query(AgentSession)
    if current_user.role != "admin":
        query = query.filter(AgentSession.user_id == current_user.id)
    return query


def _visible_api_ids(db: Session, current_user: User):
    query = db.query(ApiDefinition.id)
    if current_user.role != "admin":
        query = query.filter(ApiDefinition.user_id == current_user.id)
    return [a.id for a in query.all()]


def _session_actor(session_user: User | None) -> tuple[str, str]:
    if not session_user:
        return "—", "—"
    return session_user.email or "—", session_user.full_name or session_user.email or "—"


def _session_prompt(session: AgentSession) -> tuple[str, str]:
    raw = (session.raw_input or "").strip()
    if session.mode == "DOC":
        if session.file_path:
            return f"Uploaded file: {Path(session.file_path).name}", raw or session.file_path or "—"
        if raw:
            return f"Uploaded file: {Path(raw).name}", raw
        return "Uploaded file", "—"
    if raw:
        if raw.startswith("Manual form:"):
            return raw, raw
        return raw, raw
    return "—", "—"


# ── Overview stats ────────────────────────────────────────────────────────────

@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = _now().replace(hour=0, minute=0, second=0, microsecond=0)

    session_query = _visible_sessions_query(db, current_user)
    total    = session_query.count()
    active   = session_query.filter(
        AgentSession.state.in_(ACTIVE_STATES),
    ).count()
    today_n  = session_query.filter(
        AgentSession.created_at >= today,
    ).count()
    saved    = session_query.filter(
        AgentSession.state == "SAVED",
    ).count()
    failed   = session_query.filter(
        AgentSession.state == "FAILED",
    ).count()
    pending  = session_query.filter(
        AgentSession.state == "HITL_PENDING",
    ).count()

    user_api_ids = _visible_api_ids(db, current_user)
    total_apis     = len(user_api_ids)
    connection_query = db.query(ChatGPTConnection)
    if current_user.role != "admin":
        connection_query = connection_query.filter(ChatGPTConnection.user_id == current_user.id)
    connected_apis = connection_query.filter(ChatGPTConnection.is_active == True).count()
    total_calls    = db.query(ToolCallLog).filter(ToolCallLog.api_definition_id.in_(user_api_ids)).count()
    calls_today    = db.query(ToolCallLog).filter(
        ToolCallLog.api_definition_id.in_(user_api_ids),
        ToolCallLog.called_at >= today,
    ).count()

    finished     = saved + failed
    success_rate = round((saved / finished) * 100) if finished else 0

    return {
        "total_sessions":   total,
        "active_sessions":  active,
        "sessions_today":   today_n,
        "saved_sessions":   saved,
        "failed_sessions":  failed,
        "pending_sessions": pending,
        "success_rate":     success_rate,
        "total_apis":       total_apis,
        "connected_apis":   connected_apis,
        "total_tool_calls": total_calls,
        "tool_calls_today": calls_today,
    }


# ── Active (currently processing) sessions ───────────────────────────────────

@router.get("/active")
def active_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(AgentSession, User)
        .outerjoin(User, User.id == AgentSession.user_id)
        .filter(
            AgentSession.state.in_(ACTIVE_STATES),
        )
    )
    if current_user.role != "admin":
        rows = rows.filter(AgentSession.user_id == current_user.id)
    rows = rows.order_by(desc(AgentSession.updated_at)).limit(10).all()
    return [
        {
            "id":              s.id,
            "mode":            s.mode or "UNKNOWN",
            "state":           s.state,
            "api_name":        _api_name(s),
            "user_email":      user.email or "—",
            "user_name":       user.full_name or user.email or "—",
            "elapsed_seconds": _elapsed(s.created_at),
            "updated_seconds": _elapsed(s.updated_at),
        }
        for s, user in rows
    ]


# ── Recent session history ────────────────────────────────────────────────────

@router.get("/sessions")
def recent_sessions(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(AgentSession, User)
        .outerjoin(User, User.id == AgentSession.user_id)
    )
    if current_user.role != "admin":
        rows = rows.filter(AgentSession.user_id == current_user.id)
    rows = (
        rows
        .order_by(desc(AgentSession.created_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "id":           s.id,
            "mode":         s.mode or "UNKNOWN",
            "state":        s.state,
            "api_name":     _api_name(s),
            "test_verdict": _test_summary(s.api_test_results),
            "user_email":   user.email or "—",
            "user_name":    user.full_name or user.email or "—",
            "prompt":       _session_prompt(s)[0],
            "raw_input":    _session_prompt(s)[1][:180],
            "created_at":   s.created_at.isoformat(),
            "duration_ms":  int((s.updated_at - s.created_at).total_seconds() * 1000),
            "error":        (s.error_log or [{}])[-1].get("error") if s.state == "FAILED" else None,
        }
        for s, user in rows
    ]


# ── Tool call log ─────────────────────────────────────────────────────────────

@router.get("/tool-calls")
def tool_call_log(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_api_ids = _visible_api_ids(db, current_user)
    rows = (
        db.query(ToolCallLog, ApiDefinition)
        .join(ApiDefinition, ToolCallLog.api_definition_id == ApiDefinition.id, isouter=True)
        .filter(ToolCallLog.api_definition_id.in_(user_api_ids))
        .order_by(desc(ToolCallLog.called_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "id":             log.id,
            "api_name":       api.name if api else "—",
            "endpoint_name":  log.endpoint_name,
            "arguments":      log.arguments,
            "result_preview": (log.result or "")[:120],
            "success":        log.success,
            "called_at":      log.called_at.isoformat(),
        }
        for log, api in rows
    ]


# ── Pipeline stats (state distribution) ──────────────────────────────────────

@router.get("/pipeline")
def pipeline_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func
    rows = (
        db.query(AgentSession.state, func.count())
        .filter(AgentSession.user_id == current_user.id)
        .group_by(AgentSession.state)
        .all()
    )
    return {state: count for state, count in rows}


@router.get("/audit")
def audit_trail(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(ChatAuditLog).order_by(desc(ChatAuditLog.created_at)).limit(limit).all()
    if current_user.role != "admin":
        rows = [r for r in rows if r.user_id == current_user.id]
    return [
        {
            "id": r.id,
            "session_id": r.session_id,
            "user_email": r.user_email or "—",
            "user_name": r.user_name or r.user_email or "—",
            "message": r.message,
            "response": r.response or "—",
            "model": r.model or "—",
            "status": r.status or "—",
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
