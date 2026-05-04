import json
import re
import httpx
from typing import Any
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from openai import AsyncOpenAI, AsyncAzureOpenAI

from config import settings
from database import get_db
from utils.encryption import decrypt_creds
from models.api_definition import ApiDefinition, ApiEndpoint
from models.chatgpt_connection import ChatGPTConnection, ToolCallLog
from translators.openai_translator import api_to_tools, resolve_tool_call
from schemas.chatgpt import (
    ConnectResponse, ChatRequest, ChatResponse,
    StatsResponse, ToolCallRecord,
)
from utils.auth import get_current_user
from models.user import User
from context.context_layer import context_layer
from orchestrator.tool_orchestrator import tool_orchestrator
from models.token_usage import TokenUsage
from models.chat_audit import ChatAuditLog

_PRICE_INPUT_PER_M  = 2.50
_PRICE_OUTPUT_PER_M = 10.00

def _calc_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens * _PRICE_INPUT_PER_M + completion_tokens * _PRICE_OUTPUT_PER_M) / 1_000_000

router = APIRouter(prefix="/api/chatgpt", tags=["chatgpt"])


def _is_mock_or_missing_openai_key() -> bool:
    key = (settings.openai_api_key or "").strip()
    return settings.mock_llm or (not settings.has_azure_openai and key in {"", "mock", "sk-..."})


def _build_llm_client():
    if settings.has_azure_openai:
        return AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_host,
            api_version=settings.azure_openai_api_version,
        ), settings.azure_openai_deployment
    return AsyncOpenAI(api_key=settings.openai_api_key), None


def _azure_client_configured() -> bool:
    host = settings.azure_openai_host
    return host.startswith("https://") and ".openai.azure.com" in host


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_api_ids = [
        a.id for a in db.query(ApiDefinition.id).filter(ApiDefinition.user_id == current_user.id).all()
    ]
    total_apis = len(user_api_ids)
    connected = db.query(ChatGPTConnection).filter(
        ChatGPTConnection.user_id == current_user.id,
        ChatGPTConnection.is_active == True,
    ).count()
    calls = db.query(ToolCallLog).filter(ToolCallLog.api_definition_id.in_(user_api_ids)).count()
    return StatsResponse(total_apis=total_apis, connected_apis=connected, total_tool_calls=calls)


# ── Registry with connection status ───────────────────────────────────────────

@router.get("/registry")
def list_all_with_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apis = (
        db.query(ApiDefinition)
        .filter(ApiDefinition.user_id == current_user.id)
        .order_by(ApiDefinition.created_at.desc())
        .all()
    )
    connected_ids = {
        c.api_definition_id
        for c in db.query(ChatGPTConnection).filter(
            ChatGPTConnection.user_id == current_user.id,
            ChatGPTConnection.is_active == True,
        ).all()
    }
    return [
        {
            "id": api.id,
            "name": api.name,
            "description": api.description,
            "base_url": api.base_url,
            "visibility": api.visibility,
            "endpoint_count": len(api.endpoints),
            "is_connected": api.id in connected_ids,
            "tools": api_to_tools(api),
        }
        for api in apis
    ]


# ── Connect / Disconnect ───────────────────────────────────────────────────────

@router.post("/connect/{api_id}", response_model=ConnectResponse)
def connect_api(
    api_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api = db.query(ApiDefinition).filter(
        ApiDefinition.id == api_id, ApiDefinition.user_id == current_user.id
    ).first()
    if not api:
        raise HTTPException(404, "API not found")

    existing = db.query(ChatGPTConnection).filter(
        ChatGPTConnection.api_definition_id == api_id,
        ChatGPTConnection.user_id == current_user.id,
        ChatGPTConnection.is_active == True,
    ).first()
    if existing:
        return ConnectResponse(api_definition_id=api_id, connected=True, message="Already connected")

    db.add(ChatGPTConnection(id=str(uuid4()), api_definition_id=api_id, user_id=current_user.id))
    db.commit()
    return ConnectResponse(
        api_definition_id=api_id,
        connected=True,
        message=f"Connected — {len(api.endpoints)} tool(s) available",
    )


@router.delete("/disconnect/{api_id}", response_model=ConnectResponse)
def disconnect_api(
    api_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conn = db.query(ChatGPTConnection).filter(
        ChatGPTConnection.api_definition_id == api_id,
        ChatGPTConnection.user_id == current_user.id,
        ChatGPTConnection.is_active == True,
    ).first()
    if not conn:
        raise HTTPException(404, "Connection not found")
    conn.is_active = False
    db.commit()
    return ConnectResponse(api_definition_id=api_id, connected=False, message="Disconnected")


# ── Session management ────────────────────────────────────────────────────────

@router.get("/session/{session_id}")
def get_session_info(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    info = context_layer.session_info(session_id)
    if not info:
        from models.chat_audit import ChatAuditLog
        rows = (
            db.query(ChatAuditLog)
            .filter(ChatAuditLog.session_id == session_id)
            .order_by(ChatAuditLog.created_at.asc())
            .all()
        )
        if not rows:
          raise HTTPException(404, "Session not found or expired")
        history = []
        for row in rows:
            history.append({"role": "user", "content": row.message, "ts": row.created_at.isoformat()})
            if row.response:
                history.append({"role": "assistant", "content": row.response, "ts": row.created_at.isoformat(), "model": row.model})
        info = {
            "session_id": session_id,
            "turns": len(rows),
            "created_at": rows[0].created_at.isoformat(),
            "last_active": rows[-1].created_at.isoformat(),
            "history": history,
        }
    return info


@router.delete("/session/{session_id}")
def clear_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    context_layer.clear_session(session_id)
    return {"cleared": True, "session_id": session_id}


# ── Tool schema export ─────────────────────────────────────────────────────────

@router.get("/tools/{api_id}")
def get_tools_schema(
    api_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api = db.query(ApiDefinition).filter(
        ApiDefinition.id == api_id, ApiDefinition.user_id == current_user.id
    ).first()
    if not api:
        raise HTTPException(404, "API not found")
    return {"api_id": api_id, "api_name": api.name, "tools": api_to_tools(api)}


def _build_auth(creds: dict | None) -> tuple:
    if not creds:
        return None, {}, {}
    ctype = (creds.get("type") or "none").lower()
    if ctype == "basic":
        return httpx.BasicAuth(creds.get("username", ""), creds.get("password", "")), {}, {}
    if ctype == "bearer":
        return None, {"Authorization": f"Bearer {creds.get('token', '')}"}, {}
    if ctype == "api_key":
        header = creds.get("header_name", "X-API-Key")
        return None, {header: creds.get("value", "")}, {}
    if ctype == "api_key_query":
        return None, {}, {creds.get("param_name", "api_key"): creds.get("value", "")}
    return None, {}, {}


# ── Chat with tools (agentic loop) ────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_with_tools(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ── Subscription gate ─────────────────────────────────────────────────────
    if current_user.role != "admin":
        if current_user.chat_status != "approved":
            raise HTTPException(403, f"chat_access:{current_user.chat_status}")
        if current_user.credits <= 0:
            raise HTTPException(402, "insufficient_credits")

    if req.api_ids:
        apis = db.query(ApiDefinition).filter(
            ApiDefinition.id.in_(req.api_ids), ApiDefinition.user_id == current_user.id
        ).all()
    else:
        cids = [
            c.api_definition_id
            for c in db.query(ChatGPTConnection).filter(
                ChatGPTConnection.user_id == current_user.id,
                ChatGPTConnection.is_active == True,
            ).all()
        ]
        apis = db.query(ApiDefinition).filter(ApiDefinition.id.in_(cids)).all()

    all_tools = []
    for api in apis:
        all_tools.extend(api_to_tools(api))

    if not all_tools:
        return ChatResponse(response="", tool_calls=[], model="none", status="NO_TOOLS_CONNECTED")

    # ── Context Layer: always runs so session_id is always assigned ───────────
    session_id, messages = context_layer.build_messages(
        session_id=req.session_id,
        user_message=req.message,
        apis=apis,
        user_email=current_user.email,
    )

    if _is_mock_or_missing_openai_key():
        lower_message = req.message.lower()
        if "weather" in lower_message:
            mock_response = (
                "Local test response: I found the connected Sample Weather API with "
                f"{len(all_tools)} available tool(s). This is mock mode, so I cannot fetch live "
                "weather, but the ChatGPT integration flow is working."
            )
        else:
            mock_response = (
                f"Local test response: I found {len(all_tools)} connected tool(s) for your request. "
                "This confirms the MCP tool connection is working in mock mode."
            )
        _log_chat_turn(db, current_user, session_id, req.message, mock_response, "mock", "ok")
        return ChatResponse(
            response=mock_response,
            tool_calls=[],
            model="mock",
            session_id=session_id,
        )

    client, deployment = _build_llm_client()

    records: list[ToolCallRecord] = []
    turn_additions: list[dict] = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for _ in range(5):
        kwargs: dict = {"model": deployment or "gpt-4o", "messages": messages}
        if all_tools:
            kwargs["tools"] = all_tools
            kwargs["tool_choice"] = "auto"

        try:
            resp = await client.chat.completions.create(**kwargs)
        except Exception as exc:
            if deployment and _azure_client_configured():
                raise
            return ChatResponse(
                response="Azure OpenAI is not configured with a valid endpoint. Check AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT in backend/.env.",
                tool_calls=[],
                model="mock",
                status="ok",
                session_id=session_id,
            )
        msg  = resp.choices[0].message
        if resp.usage:
            total_prompt_tokens     += resp.usage.prompt_tokens
            total_completion_tokens += resp.usage.completion_tokens

        if not msg.tool_calls:
            final_msg = {"role": "assistant", "content": msg.content or ""}
            turn_additions.append(final_msg)
            context_layer.save_turn(session_id, req.message, turn_additions)
            _deduct_and_log(db, current_user, session_id, total_prompt_tokens, total_completion_tokens)
            _log_chat_turn(db, current_user, session_id, req.message, msg.content or "", deployment or "gpt-4o", "ok")
            return ChatResponse(
                response=msg.content or "",
                tool_calls=records,
                model="gpt-4o",
                session_id=session_id,
            )

        # Save assistant message with tool_calls before results (OpenAI ordering)
        assistant_dict = msg.model_dump(exclude_unset=True)
        messages.append(assistant_dict)
        turn_additions.append(assistant_dict)

        # ── Orchestrator: parallel execution + retry ──────────────────────────
        results = await tool_orchestrator.execute_all(msg.tool_calls, db, dry_run=req.dry_run)

        for er in results:
            # Persist to ToolCallLog if we resolved the endpoint
            api_obj, ep_obj = resolve_tool_call(er.tool_name, db)
            if api_obj:
                db.add(ToolCallLog(
                    id=str(uuid4()),
                    api_definition_id=api_obj.id,
                    endpoint_name=er.endpoint,
                    arguments=json.dumps(er.arguments),
                    result=er.result_text[:1000],
                    success=er.success,
                ))
                db.commit()

            records.append(ToolCallRecord(
                tool_name=er.tool_name,
                api_name=er.api_name,
                endpoint=er.endpoint,
                arguments=er.arguments,
                result=er.result_text,
                success=er.success,
            ))
            tool_msg = {
                "role": "tool",
                "tool_call_id": er.tool_call_id,
                "content": er.result_text,
            }
            messages.append(tool_msg)
            turn_additions.append(tool_msg)

    try:
        final = await client.chat.completions.create(model=deployment or "gpt-4o", messages=messages)
    except Exception:
        if deployment and _azure_client_configured():
            raise
        fallback_msg = "Azure OpenAI is not configured with a valid endpoint. Check AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT in backend/.env."
        _log_chat_turn(db, current_user, session_id, req.message, fallback_msg, "mock", "ok")
        return ChatResponse(
            response=fallback_msg,
            tool_calls=[],
            model="mock",
            status="ok",
            session_id=session_id,
        )
    if final.usage:
        total_prompt_tokens     += final.usage.prompt_tokens
        total_completion_tokens += final.usage.completion_tokens
    final_msg = {"role": "assistant", "content": final.choices[0].message.content or ""}
    turn_additions.append(final_msg)
    context_layer.save_turn(session_id, req.message, turn_additions)
    _deduct_and_log(db, current_user, session_id, total_prompt_tokens, total_completion_tokens)
    _log_chat_turn(db, current_user, session_id, req.message, final.choices[0].message.content or "", deployment or "gpt-4o", "ok")
    return ChatResponse(
        response=final.choices[0].message.content or "",
        tool_calls=records,
        model=deployment or "gpt-4o",
        session_id=session_id,
    )



def _deduct_and_log(
    db: Session, user: User, session_id: str,
    prompt_tokens: int, completion_tokens: int,
):
    if user.role == "admin" or (prompt_tokens == 0 and completion_tokens == 0):
        return
    cost = _calc_cost(prompt_tokens, completion_tokens)
    user.credits = max(0.0, round(user.credits - cost, 6))
    db.add(TokenUsage(
        id=str(uuid4()),
        user_id=user.id,
        session_id=session_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost_usd=cost,
    ))
    db.commit()


def _log_chat_turn(
    db: Session,
    user: User,
    session_id: str,
    message: str,
    response: str,
    model: str,
    status: str,
):
    db.add(ChatAuditLog(
        id=str(uuid4()),
        session_id=session_id,
        user_id=user.id,
        user_email=user.email,
        user_name=user.full_name or user.email,
        message=message,
        response=response,
        model=model,
        status=status,
    ))
    db.commit()
