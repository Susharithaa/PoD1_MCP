"""ApiSaver — persists the validated API to the api_definitions table."""

import uuid
from sqlalchemy.orm import Session
from agents.base import BaseAgent
from models.agent_session import AgentSession
from models.api_definition import ApiDefinition, ApiEndpoint
from utils.encryption import encrypt_creds, decrypt_creds


class ApiSaver(BaseAgent):
    name = "api_saver"

    def __init__(self, db: Session):
        self.db = db

    async def run(self, session: AgentSession) -> AgentSession:
        api = session.final_api or session.draft_api or {}
        auth_store = decrypt_creds(session.auth_credentials) or {}

        definition = ApiDefinition(
            id=str(uuid.uuid4()),
            name=api.get("name", "Unnamed API"),
            description=api.get("description"),
            base_url=api.get("base_url"),
            visibility="PRIVATE",
            source_session_id=session.id,
            user_id=session.user_id,
        )

        for i, ep in enumerate(api.get("endpoints", [])):
            creds = _pick_creds(auth_store, i)
            definition.endpoints.append(
                ApiEndpoint(
                    id=str(uuid.uuid4()),
                    api_definition_id=definition.id,
                    name=ep.get("name", "endpoint"),
                    description=ep.get("description"),
                    path=ep.get("path", "/"),
                    method=ep.get("method", "GET").upper(),
                    input_schema=ep.get("input_schema"),
                    output_schema=ep.get("output_schema"),
                    headers=ep.get("headers", []),
                    auth_type=ep.get("auth_type", "NONE"),
                    auth_credentials=encrypt_creds(creds),
                )
            )

        self.db.add(definition)
        self.db.commit()
        self.db.refresh(definition)

        session.api_definition_id = definition.id
        return session


def _pick_creds(auth_store: dict, index: int) -> dict | None:
    """Return the credentials dict to attach to an endpoint at save time."""
    if not auth_store:
        return None
    mode = auth_store.get("mode", "same")
    if mode == "per_endpoint":
        creds_list = auth_store.get("credentials", [])
        creds = creds_list[index] if index < len(creds_list) else None
    else:
        creds = auth_store
    if not creds or creds.get("type", "none") == "none":
        return None
    return creds
