"""Registry routes — browse and manage published API definitions."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.api_definition import ApiDefinition, ApiEndpoint
from schemas.agent import ApiDefinitionResponse
from schemas.registry import (
    ApiUpdateRequest, ApiAuthUpdateRequest, EndpointRequest,
    EndpointResponse, ApiDetailResponse,
)
from utils.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/api/registry", tags=["registry"])


def _get_owned_api(api_id: str, db: Session, current_user: User) -> ApiDefinition:
    api = db.query(ApiDefinition).filter(
        ApiDefinition.id == api_id, ApiDefinition.user_id == current_user.id
    ).first()
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    return api


@router.get("/", response_model=list[ApiDefinitionResponse])
def list_apis(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ApiDefinition)
        .filter(ApiDefinition.user_id == current_user.id)
        .order_by(ApiDefinition.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{api_id}", response_model=ApiDetailResponse)
def get_api(
    api_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_api(api_id, db, current_user)


@router.patch("/{api_id}", response_model=ApiDetailResponse)
def update_api(
    api_id: str,
    body: ApiUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api = _get_owned_api(api_id, db, current_user)
    if body.name is not None:
        api.name = body.name
    if body.description is not None:
        api.description = body.description
    if body.base_url is not None:
        api.base_url = body.base_url
    if body.version is not None:
        api.version = body.version
    api.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(api)
    return api


@router.patch("/{api_id}/auth", response_model=ApiDetailResponse)
def update_auth(
    api_id: str,
    body: ApiAuthUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api = _get_owned_api(api_id, db, current_user)
    for ep in api.endpoints:
        ep.auth_type = body.auth_type
    api.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(api)
    return api


@router.post("/{api_id}/endpoints", response_model=EndpointResponse, status_code=201)
def create_endpoint(
    api_id: str,
    body: EndpointRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_api(api_id, db, current_user)
    ep = ApiEndpoint(
        id=str(uuid.uuid4()),
        api_definition_id=api_id,
        name=body.name,
        description=body.description,
        path=body.path,
        method=body.method.upper(),
        auth_type=body.auth_type or "NONE",
        input_schema=body.input_schema,
        output_schema=body.output_schema,
        headers=body.headers or [],
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return ep


@router.put("/{api_id}/endpoints/{ep_id}", response_model=EndpointResponse)
def update_endpoint(
    api_id: str,
    ep_id: str,
    body: EndpointRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_api(api_id, db, current_user)
    ep = db.query(ApiEndpoint).filter(
        ApiEndpoint.id == ep_id, ApiEndpoint.api_definition_id == api_id
    ).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    ep.name          = body.name
    ep.description   = body.description
    ep.path          = body.path
    ep.method        = body.method.upper()
    ep.auth_type     = body.auth_type or "NONE"
    ep.input_schema  = body.input_schema
    ep.output_schema = body.output_schema
    ep.headers       = body.headers or []
    db.commit()
    db.refresh(ep)
    return ep


@router.delete("/{api_id}/endpoints/{ep_id}", status_code=204)
def delete_endpoint(
    api_id: str,
    ep_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_api(api_id, db, current_user)
    ep = db.query(ApiEndpoint).filter(
        ApiEndpoint.id == ep_id, ApiEndpoint.api_definition_id == api_id
    ).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    db.delete(ep)
    db.commit()


@router.delete("/{api_id}", status_code=204)
def delete_api(
    api_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api = _get_owned_api(api_id, db, current_user)
    db.delete(api)
    db.commit()
