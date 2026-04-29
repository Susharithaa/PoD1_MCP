"""Tests: rate limiting returns 429 after limit is hit."""
import pytest


def test_login_rate_limit(client):
    """10 requests/minute — hit it with 11 back-to-back calls."""
    # Register first so the requests are well-formed
    client.post("/api/auth/register", json={"email": "rl@test.com", "password": "pass"})

    responses = []
    for _ in range(12):
        r = client.post("/api/auth/login", json={"email": "rl@test.com", "password": "wrong"})
        responses.append(r.status_code)

    assert 429 in responses, f"Expected 429 in {responses}"


def test_register_rate_limit(client):
    """5 requests/minute — hit with 6 unique emails."""
    responses = []
    for i in range(7):
        r = client.post("/api/auth/register", json={
            "email": f"ratelimit{i}@test.com",
            "password": "pass",
        })
        responses.append(r.status_code)

    assert 429 in responses, f"Expected 429 in {responses}"
