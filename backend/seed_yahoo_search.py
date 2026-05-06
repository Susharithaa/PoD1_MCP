"""
Seed script — imports an OpenAPI YAML into the database as an ApiDefinition.

Usage (from the backend directory):
    python seed_yahoo_search.py                          # Yahoo Search US
    python seed_yahoo_search.py ../testing/<file>.yaml   # specific file
    python seed_yahoo_search.py --all-japan              # all 7 Yahoo Japan APIs

Auth is auto-detected from the server URL:
    serpapi.com   -> SERPAPI_KEY  (param: api_key)
    yahooapis.jp  -> YAHOO_JAPAN_APP_ID  (param: appid)

Idempotent: running twice will not create duplicate entries.
"""

import sys
import uuid
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from database import SessionLocal
from models.api_definition import ApiDefinition, ApiEndpoint
from models.chatgpt_connection import ChatGPTConnection
from models.user import User
from utils.encryption import encrypt_creds


DEFAULT_YAML = Path(__file__).parent.parent / "testing" / "yahoo_search_us.yaml"
TESTING_DIR  = Path(__file__).parent.parent / "testing"

YAHOO_JAPAN_YAMLS = [
    "yahoo_japan_area_info.yaml",
    "yahoo_japan_prefecture_info.yaml",
    "yahoo_japan_route.yaml",
    "yahoo_japan_station_info.yaml",
    "yahoo_japan_nearest_station.yaml",
    "yahoo_japan_combo_area_line_station.yaml",
    "yahoo_japan_combo_pref_route_station.yaml",
]

JQUANTS_YAMLS = [
    "jquants_daily_bars.yaml",
]


def _build_input_schema(parameters: list[dict]) -> dict:
    properties = {}
    required = []
    for p in parameters:
        s = p.get("schema", {})
        prop: dict = {"description": p.get("description", ""), "type": s.get("type", "string")}
        if "enum"    in s: prop["enum"]    = s["enum"]
        if "default" in s: prop["default"] = s["default"]
        if "minimum" in s: prop["minimum"] = s["minimum"]
        if "maximum" in s: prop["maximum"] = s["maximum"]
        properties[p["name"]] = prop
        if p.get("required"):
            required.append(p["name"])
    return {"type": "object", "properties": properties, "required": required}


def _detect_auth(base_url: str) -> dict:
    if "serpapi.com" in base_url:
        return {"type": "api_key_query", "param_name": "api_key", "value": settings.serpapi_key}
    if "yahooapis.jp" in base_url:
        return {"type": "api_key_query", "param_name": "appid",   "value": settings.yahoo_japan_app_id}
    if "jquants.com" in base_url:
        return {"type": "api_key", "header_name": "x-api-key",   "value": settings.jquants_api_key}
    # heartrails.com and other open APIs need no auth
    return {"type": "none"}


def seed(db: Session, user_id: str, yaml_path: Path) -> None:
    spec     = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    api_name = spec["info"]["title"]
    base_url = spec["servers"][0]["url"]

    existing = db.query(ApiDefinition).filter(
        ApiDefinition.name == api_name, ApiDefinition.user_id == user_id
    ).first()
    if existing:
        print(f"  Already seeded '{api_name}' — skipping")
        return

    api_id = str(uuid.uuid4())
    db.add(ApiDefinition(
        id=api_id,
        name=api_name,
        description=spec["info"]["description"],
        base_url=base_url,
        visibility="PRIVATE",
        version=spec["info"]["version"],
        tags=["yahoo", "japan"],
        user_id=user_id,
    ))

    for path, methods in spec["paths"].items():
        for method, ep_spec in methods.items():
            auth_creds = _detect_auth(base_url)
            db.add(ApiEndpoint(
                id=str(uuid.uuid4()),
                api_definition_id=api_id,
                name=ep_spec["operationId"],
                description=ep_spec["description"],
                path=path,
                method=method.upper(),
                input_schema=_build_input_schema(ep_spec.get("parameters", [])),
                output_schema=None,
                headers=[],
                auth_type=auth_creds["type"],
                auth_credentials=encrypt_creds(auth_creds),
            ))

    db.commit()

    # Auto-connect for this user so the chat endpoint can use it immediately
    existing_conn = db.query(ChatGPTConnection).filter(
        ChatGPTConnection.api_definition_id == api_id,
        ChatGPTConnection.user_id == user_id,
    ).first()
    if not existing_conn:
        db.add(ChatGPTConnection(
            id=str(uuid.uuid4()),
            api_definition_id=api_id,
            user_id=user_id,
            is_active=True,
        ))
        db.commit()

    print(f"  Seeded and connected '{api_name}' (id={api_id[:8]}...)")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--all-japan":
        yaml_paths = [TESTING_DIR / name for name in YAHOO_JAPAN_YAMLS]
    elif len(sys.argv) > 1 and sys.argv[1] == "--jquants":
        yaml_paths = [TESTING_DIR / name for name in JQUANTS_YAMLS]
    elif len(sys.argv) > 1 and sys.argv[1] == "--all":
        yaml_paths = (
            [TESTING_DIR / name for name in YAHOO_JAPAN_YAMLS]
            + [TESTING_DIR / name for name in JQUANTS_YAMLS]
        )
    elif len(sys.argv) > 1:
        yaml_paths = [Path(sys.argv[1])]
    else:
        yaml_paths = [DEFAULT_YAML]

    missing = [p for p in yaml_paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"ERROR: not found: {p}", file=sys.stderr)
        sys.exit(1)

    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("No users found — start the app and register first.")
            return
        for yaml_path in yaml_paths:
            print(f"\n{yaml_path.name}")
            for user in users:
                seed(db, user.id, yaml_path)
    finally:
        db.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
