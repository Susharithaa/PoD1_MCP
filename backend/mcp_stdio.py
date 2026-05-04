"""Stdio transport bridge for MCP Hub.

Reads one JSON-RPC envelope per line from stdin and forwards it to /mcp.
Set MCP_HUB_URL and MCP_API_TOKEN before running.
"""

import json
import os
import sys

import httpx


def main() -> int:
    base_url = os.getenv("MCP_HUB_URL", "http://localhost:8000").rstrip("/")
    token = os.getenv("MCP_API_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with httpx.Client(timeout=30.0) as client:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                response = client.post(f"{base_url}/mcp", headers=headers, json=payload)
                response.raise_for_status()
                print(json.dumps(response.json()), flush=True)
            except Exception as exc:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32000, "message": str(exc)},
                }), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
