from pydantic import BaseModel
from typing import Any
from datetime import datetime


class EndpointRequest(BaseModel):
    name: str
    description: str = ""
    path: str
    method: str
    auth_type: str = "NONE"
    input_schema: Any = None
    output_schema: Any = None
    headers: Any = None


class ApiUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    base_url: str | None = None
    version: str | None = None


class ApiAuthUpdateRequest(BaseModel):
    auth_type: str


class EndpointResponse(BaseModel):
    id: str
    name: str
    description: str | None
    path: str
    method: str
    auth_type: str | None
    input_schema: Any
    output_schema: Any
    headers: Any

    class Config:
        from_attributes = True


class ApiDetailResponse(BaseModel):
    id: str
    name: str
    description: str | None
    base_url: str | None
    visibility: str
    version: str
    source_session_id: str | None
    created_at: datetime
    updated_at: datetime
    endpoints: list[EndpointResponse]

    class Config:
        from_attributes = True
