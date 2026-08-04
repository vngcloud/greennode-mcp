"""Tests for the passthrough middleware (HTTP) and stdio token gate."""

from __future__ import annotations

import pytest
import sys
from greennode.agentbase_mcp_server.middleware import PassthroughIdentityMiddleware
from greennode.mcp_core.http import user_token_var
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient


async def _root(request):
    token = user_token_var.get()
    return PlainTextResponse(f"token={token or 'none'}")


def _app():
    app = Starlette(routes=[Route("/{path:path}", _root, methods=["GET", "POST"])])
    app.add_middleware(PassthroughIdentityMiddleware)
    # add_middleware wraps the app; TestClient drives the outer middleware-as-app.
    return app


def test_http_401_without_bearer():
    with TestClient(_app()) as client:
        r = client.post("/mcp")
    assert r.status_code == 401
    assert "Bearer" in r.headers.get("WWW-Authenticate", "")


def test_http_health_open():
    with TestClient(_app()) as client:
        r = client.get("/health")
    assert r.status_code == 200


def test_http_seeds_user_token_from_bearer():
    with TestClient(_app()) as client:
        r = client.post("/mcp", headers={"Authorization": "Bearer abc123"})
    assert r.status_code == 200
    assert r.text == "token=abc123"


def test_http_rejects_empty_bearer():
    with TestClient(_app()) as client:
        r = client.post("/mcp", headers={"Authorization": "Bearer "})
    assert r.status_code == 401


def test_stdio_missing_token_exits_nonzero(monkeypatch, tmp_path):
    """main() with stdio and no GREENNODE_MCP_TOKEN env exits non-zero."""
    from greennode.agentbase_mcp_server import server

    monkeypatch.setattr(sys, "argv", ["agentbase-mcp-server"])
    monkeypatch.delenv("GREENNODE_MCP_TOKEN", raising=False)
    monkeypatch.delenv("TOKEN_ENV", raising=False)
    with pytest.raises(SystemExit):
        server.main()
