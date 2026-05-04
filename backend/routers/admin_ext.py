import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.agent_session import AgentSession
from models.api_definition import ApiDefinition
from models.chatgpt_connection import ChatGPTConnection, ToolCallLog
from models.operational import AuditLog, Incident, PluginSetting, RolePermission
from models.token_usage import TokenUsage
from models.user import User
from utils.auth import require_admin
from utils.masking import mask_sensitive
from utils.safety import get_system_controls

router = APIRouter(prefix="/api/admin", tags=["admin-ops"])


@router.get("/audit")
def audit_trail(limit: int = 100, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [mask_sensitive({
        "id": row.id,
        "actor_email": row.actor_email,
        "action": row.action,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "request_id": row.request_id,
        "ip_address": row.ip_address,
        "metadata": row.metadata_json,
        "created_at": row.created_at.isoformat(),
    }) for row in rows]


@router.get("/logs/live")
def live_logs(limit: int = 100, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return audit_trail(limit=limit, db=db, admin=admin)


@router.get("/llm-costs")
def llm_costs(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    totals = db.query(
        func.count(TokenUsage.id),
        func.coalesce(func.sum(TokenUsage.prompt_tokens), 0),
        func.coalesce(func.sum(TokenUsage.completion_tokens), 0),
        func.coalesce(func.sum(TokenUsage.cost_usd), 0.0),
    ).first()
    recent = db.query(TokenUsage).order_by(TokenUsage.created_at.desc()).limit(30).all()
    return {
        "request_count": totals[0],
        "prompt_tokens": totals[1],
        "completion_tokens": totals[2],
        "cost_usd": round(float(totals[3]), 6),
        "recent": [
            {
                "session_id": row.session_id,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "cost_usd": row.cost_usd,
                "created_at": row.created_at.isoformat(),
            }
            for row in recent
        ],
    }


@router.get("/incidents")
def incidents(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [
        {
            "id": row.id,
            "title": row.title,
            "severity": row.severity,
            "status": row.status,
            "source": row.source,
            "summary": row.summary,
            "events": row.events,
            "created_at": row.created_at.isoformat(),
        }
        for row in db.query(Incident).order_by(Incident.created_at.desc()).limit(100).all()
    ]


@router.post("/incidents/aggregate")
def aggregate_incidents(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    failed = db.query(AgentSession).filter(AgentSession.state == "FAILED").count()
    unreachable = db.query(ToolCallLog).filter(ToolCallLog.success == False).count()
    incident = Incident(
        id=str(uuid.uuid4()),
        title="Automated health aggregation",
        severity="HIGH" if failed or unreachable else "LOW",
        status="OPEN" if failed or unreachable else "RESOLVED",
        source="aggregator",
        summary=f"{failed} failed sessions, {unreachable} failed tool calls",
        events=[{"type": "summary", "failed_sessions": failed, "failed_tool_calls": unreachable}],
    )
    db.add(incident)
    db.commit()
    return {"incident_id": incident.id, "summary": incident.summary}


@router.get("/plugins")
def list_plugins(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [
        {"id": row.id, "name": row.name, "enabled": row.enabled, "config": mask_sensitive(row.config), "updated_at": row.updated_at.isoformat()}
        for row in db.query(PluginSetting).order_by(PluginSetting.name).all()
    ]


@router.put("/plugins/{name}")
def upsert_plugin(name: str, body: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    row = db.query(PluginSetting).filter(PluginSetting.name == name).first()
    if not row:
        row = PluginSetting(id=str(uuid.uuid4()), name=name)
        db.add(row)
    row.enabled = bool(body.get("enabled", row.enabled))
    row.config = body.get("config", row.config or {})
    row.updated_by = admin.id
    db.commit()
    return {"ok": True}


@router.get("/rbac")
def get_rbac(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.query(RolePermission).order_by(RolePermission.role).all()
    if not rows:
        return {"admin": ["*"], "user": ["tools:read", "mcp:read"]}
    return {row.role: row.scopes for row in rows}


@router.put("/rbac")
def set_rbac(body: dict[str, list[str]], db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    for role, scopes in body.items():
        row = db.query(RolePermission).filter(RolePermission.role == role).first()
        if not row:
            row = RolePermission(id=str(uuid.uuid4()), role=role)
            db.add(row)
        row.scopes = scopes
    db.commit()
    return {"ok": True}


@router.get("/config/export")
def export_config(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "apis": [
            {
                "id": api.id,
                "name": api.name,
                "description": api.description,
                "base_url": api.base_url,
                "version": api.version,
                "endpoints": [
                    {
                        "name": ep.name,
                        "description": ep.description,
                        "path": ep.path,
                        "method": ep.method,
                        "input_schema": ep.input_schema,
                        "output_schema": ep.output_schema,
                        "auth_type": ep.auth_type,
                    }
                    for ep in api.endpoints
                ],
            }
            for api in db.query(ApiDefinition).all()
        ],
        "connections": [
            {"api_definition_id": row.api_definition_id, "user_id": row.user_id, "is_active": row.is_active}
            for row in db.query(ChatGPTConnection).all()
        ],
        "plugins": list_plugins(db=db, admin=admin),
        "rbac": get_rbac(db=db, admin=admin),
    }
    return Response(
        content=json.dumps(mask_sensitive(payload), default=str, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=mcp-hub-config.json"},
    )


@router.post("/config/import")
def import_config(body: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    # Conservative import: settings-like objects only. API definitions are exported for backup,
    # but not blindly imported here to avoid overwriting user-owned records.
    for plugin in body.get("plugins", []):
        upsert_plugin(plugin["name"], plugin, db=db, admin=admin)
    if isinstance(body.get("rbac"), dict):
        set_rbac(body["rbac"], db=db, admin=admin)
    return {"ok": True, "imported": {"plugins": len(body.get("plugins", [])), "rbac": bool(body.get("rbac"))}}


@router.get("/system-controls")
def system_controls(admin: User = Depends(require_admin)):
    return get_system_controls()


@router.put("/system-controls")
def update_system_controls(body: dict[str, Any], db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    row = db.query(PluginSetting).filter(PluginSetting.name == "system-controls").first()
    if not row:
        row = PluginSetting(id=str(uuid.uuid4()), name="system-controls")
        db.add(row)
    current = dict(row.config or {})
    for key in ("emergency_stop", "dry_run_tools", "max_tool_execution_ms"):
        if key in body:
            current[key] = body[key]
    row.enabled = True
    row.config = current
    row.updated_by = admin.id
    db.commit()
    return get_system_controls()
