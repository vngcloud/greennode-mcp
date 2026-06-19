"""Tests for the opt-in auth-debug request summarizer."""

from __future__ import annotations

import jwt
from greennode.vks_mcp_server.auth_debug import summarize_request


def test_no_authorization_header():
    s = summarize_request("GET", "/mcp", {})
    assert s["method"] == "GET"
    assert s["path"] == "/mcp"
    assert s["has_authorization"] is False
    assert s["auth_scheme"] is None
    assert "token_prefix" not in s
    assert s["forwarding_headers"] == {}


def test_bearer_token_is_redacted_never_full():
    token = "abcdefghijklmnopqrstuvwxyz0123456789"
    s = summarize_request("POST", "/mcp", {"Authorization": f"Bearer {token}"})
    assert s["has_authorization"] is True
    assert s["auth_scheme"] == "Bearer"
    assert s["token_present"] is True
    assert s["token_len"] == len(token)
    assert s["token_prefix"] == token[:6]
    # The full token must never appear anywhere in the summary.
    assert token not in repr(s)
