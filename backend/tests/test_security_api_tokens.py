"""Security API token creation and MCP auth coverage."""


def _register(client, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": email.split("@")[0]},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _tools_list(client, token: str):
    return client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": "tools", "method": "tools/list", "params": {}},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_user_can_create_mcp_read_api_token_and_use_it_for_tools_list(client):
    _register(client, "admin-security@test.com")
    user_headers = _register(client, "token-user@test.com")

    create = client.post(
        "/api/security/tokens",
        json={"name": "Codex MCP token", "scopes": ["mcp:read"]},
        headers=user_headers,
    )

    assert create.status_code == 201, create.text
    created = create.json()
    assert created["name"] == "Codex MCP token"
    assert created["scopes"] == ["mcp:read"]
    assert created["token"].startswith("mcp_")

    listed = client.get("/api/security/tokens", headers=user_headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["token_prefix"] == created["token_prefix"]
    assert "token" not in listed.json()[0]

    tools = _tools_list(client, created["token"])
    assert tools.status_code == 200, tools.text
    body = tools.json()
    assert "error" not in body
    names = {tool["name"] for tool in body["result"]["tools"]}
    assert "hub.list_tools" in names


def test_api_token_without_mcp_read_scope_cannot_use_tools_list(client):
    _register(client, "admin-security@test.com")
    user_headers = _register(client, "token-user@test.com")

    create = client.post(
        "/api/security/tokens",
        json={"name": "Non MCP token", "scopes": ["tools:read"]},
        headers=user_headers,
    )
    assert create.status_code == 201, create.text

    tools = _tools_list(client, create.json()["token"])

    assert tools.status_code == 403
    assert tools.json()["detail"] == "Missing scope: mcp:read"
