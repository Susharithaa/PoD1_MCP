from pydantic import BaseModel
from typing import Any
from datetime import datetime


class StartChatRequest(BaseModel):
    message: str


# ── Manual API builder ────────────────────────────────────────────────────────

class ParamSpec(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    description: str = ""


class EndpointSpec(BaseModel):
    method: str
    path: str
    name: str = ""
    description: str = ""
    auth_type: str = ""
    parameters: list[ParamSpec] = []


class ManualApiRequest(BaseModel):
    name: str
    description: str = ""
    base_url: str
    version: str = "1.0.0"
    auth_type: str = "none"
    auth_header: str = ""
    auth_credentials: Any = None
    endpoints: list[EndpointSpec] = []


class StartDocRequest(BaseModel):
    # file comes via multipart — this is just for OpenAPI docs
    pass


class HITLSubmitRequest(BaseModel):
    edits: dict[str, Any]
    auth_credentials: Any = None
    save_anyway: bool = False


class SessionResponse(BaseModel):
    id: str
    mode: str | None
    state: str
    draft_api: Any
    final_api: Any
    confidence_map: Any
    validation_errors: list[str] | None
    api_test_results: list[Any] | None
    api_definition_id: str | None
    error_log: list[Any] | None
    auth_credentials: Any = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiDefinitionResponse(BaseModel):
    id: str
    name: str
    description: str | None
    base_url: str | None
    visibility: str
    version: str
    source_session_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True
