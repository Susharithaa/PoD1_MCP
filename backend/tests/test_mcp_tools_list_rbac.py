"""MCP tools/list RBAC and discoverability scenarios."""

from uuid import uuid4

from database import SessionLocal
from models.api_definition import ApiDefinition, ApiEndpoint


FIXED_TOOL_NAMES = {
    "hub.list_registered_apis",
    "hub.list_tools",
    "hub.get_tool_schema",
    "expense.get_application_info",
    "expense.list_reports",
    "expense.download_file",
}


def _register(client, email: str, password: str = "pass123") -> tuple[dict, dict]:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    user = client.get("/api/auth/me", headers=headers).json()
    return headers, user


def _create_mcp_token(client, login_headers: dict, name: str) -> dict:
    response = client.post(
        "/api/security/tokens",
        json={"name": name, "scopes": ["mcp:read"]},
        headers=login_headers,
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _seed_three_tools_for_user(user_id: str, prefix: str) -> set[str]:
    expected_tool_names = set()
    with SessionLocal() as db:
        for i in range(1, 4):
            api = ApiDefinition(
                id=str(uuid4()),
                name=f"{prefix.title()} API {i}",
                description=f"{prefix} test API {i}",
                base_url=f"https://{prefix}{i}.example.com",
                user_id=user_id,
            )
            endpoint_name = f"{prefix}_tool_{i}"
            endpoint = ApiEndpoint(
                id=str(uuid4()),
                api_definition_id=api.id,
                name=endpoint_name,
                description=f"{prefix} endpoint {i}",
                path=f"/tool-{i}",
                method="GET",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": [],
                },
                output_schema={"type": "object", "properties": {}},
            )
            db.add(api)
            db.add(endpoint)
            expected_tool_names.add(endpoint_name)
        db.commit()
    return expected_tool_names


def _mcp_tool_names(client, headers: dict) -> set[str]:
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "tools", "method": "tools/list", "params": {}},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "error" not in body, body
    return {tool["name"] for tool in body["result"]["tools"]}


def _setup_three_users_with_three_tools_each(client):
    admin_headers, admin = _register(client, "admin-rbac@test.com")
    users = {}
    all_dynamic_tools = set()

    for prefix in ("alpha", "bravo", "charlie"):
        login_headers, user = _register(client, f"{prefix}@test.com")
        mcp_headers = _create_mcp_token(client, login_headers, f"{prefix} MCP token")
        expected_tools = _seed_three_tools_for_user(user["id"], prefix)
        users[prefix] = {
            "login_headers": login_headers,
            "mcp_headers": mcp_headers,
            "user": user,
            "expected_tools": expected_tools,
        }
        all_dynamic_tools.update(expected_tools)

    return admin_headers, admin, users, all_dynamic_tools


def test_each_regular_user_lists_only_their_three_mcp_tools(client):
    _, _, users, all_dynamic_tools = _setup_three_users_with_three_tools_each(client)

    for prefix, context in users.items():
        names = _mcp_tool_names(client, context["mcp_headers"])

        assert FIXED_TOOL_NAMES.issubset(names)
        assert context["expected_tools"].issubset(names)
        assert names.intersection(all_dynamic_tools) == context["expected_tools"], (
            f"{prefix} should only see its own dynamic MCP tools"
        )


def test_regular_login_jwt_without_mcp_scope_cannot_list_tools(client):
    _, _, users, _ = _setup_three_users_with_three_tools_each(client)

    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "tools", "method": "tools/list", "params": {}},
        headers=users["alpha"]["login_headers"],
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing scope: mcp:read"


def test_admin_lists_all_users_mcp_tools(client):
    admin_headers, _, _, all_dynamic_tools = _setup_three_users_with_three_tools_each(client)

    names = _mcp_tool_names(client, admin_headers)

    assert FIXED_TOOL_NAMES.issubset(names)
    assert all_dynamic_tools.issubset(names)
    assert len(names.intersection(all_dynamic_tools)) == 9


def test_promoted_admin_lists_all_users_mcp_tools(client):
    admin_headers, _, users, all_dynamic_tools = _setup_three_users_with_three_tools_each(client)
    bravo = users["bravo"]["user"]

    promote = client.patch(
        f"/api/auth/admin/users/{bravo['id']}/role",
        json={"role": "admin"},
        headers=admin_headers,
    )
    assert promote.status_code == 200, promote.text
    assert promote.json()["role"] == "admin"

    names = _mcp_tool_names(client, users["bravo"]["login_headers"])

    assert FIXED_TOOL_NAMES.issubset(names)
    assert all_dynamic_tools.issubset(names)
    assert len(names.intersection(all_dynamic_tools)) == 9
