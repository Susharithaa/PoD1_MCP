from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models.agent_session import AgentSession
from models.api_definition import ApiDefinition
from models.chatgpt_connection import ChatGPTConnection, ToolCallLog
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


# ── Overview stats ────────────────────────────────────────────────────────────

@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = _now().replace(hour=0, minute=0, second=0, microsecond=0)

    total    = db.query(AgentSession).filter(AgentSession.user_id == current_user.id).count()
    active   = db.query(AgentSession).filter(
        AgentSession.user_id == current_user.id,
        AgentSession.state.in_(ACTIVE_STATES),
    ).count()
    today_n  = db.query(AgentSession).filter(
        AgentSession.user_id == current_user.id,
        AgentSession.created_at >= today,
    ).count()
    saved    = db.query(AgentSession).filter(
        AgentSession.user_id == current_user.id,
        AgentSession.state == "SAVED",
    ).count()
    failed   = db.query(AgentSession).filter(
        AgentSession.user_id == current_user.id,
        AgentSession.state == "FAILED",
    ).count()
    pending  = db.query(AgentSession).filter(
        AgentSession.user_id == current_user.id,
        AgentSession.state == "HITL_PENDING",
    ).count()

    user_api_ids = [
        a.id for a in db.query(ApiDefinition.id).filter(ApiDefinition.user_id == current_user.id).all()
    ]
    total_apis     = len(user_api_ids)
    connected_apis = db.query(ChatGPTConnection).filter(
        ChatGPTConnection.user_id == current_user.id,
        ChatGPTConnection.is_active == True,
    ).count()
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
        db.query(AgentSession)
        .filter(
            AgentSession.user_id == current_user.id,
            AgentSession.state.in_(ACTIVE_STATES),
        )
        .order_by(desc(AgentSession.updated_at))
        .limit(10)
        .all()
    )
    return [
        {
            "id":              s.id,
            "mode":            s.mode or "UNKNOWN",
            "state":           s.state,
            "api_name":        _api_name(s),
            "elapsed_seconds": _elapsed(s.created_at),
            "updated_seconds": _elapsed(s.updated_at),
        }
        for s in rows
    ]


# ── Recent session history ────────────────────────────────────────────────────

@router.get("/sessions")
def recent_sessions(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(AgentSession)
        .filter(AgentSession.user_id == current_user.id)
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
            "created_at":   s.created_at.isoformat(),
            "duration_ms":  int((s.updated_at - s.created_at).total_seconds() * 1000),
            "error":        (s.error_log or [{}])[-1].get("error") if s.state == "FAILED" else None,
        }
        for s in rows
    ]


# ── Tool call log ─────────────────────────────────────────────────────────────

@router.get("/tool-calls")
def tool_call_log(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_api_ids = [
        a.id for a in db.query(ApiDefinition.id).filter(ApiDefinition.user_id == current_user.id).all()
    ]
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
