"""Tests for server.py — CLI arg parsing and BearerTokenMiddleware."""
from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from greennode.greenode_mcp_server.server import BearerTokenMiddleware, _build_parser


def _parse(argv):
    return _build_parser().parse_args(argv)


# --- Arg parsing ---

def test_default_transport_is_stdio():
    args = _parse([])
    assert args.transport == "stdio"


def test_transport_http_flag():
    args = _parse(["--transport", "streamable-http"])
    assert args.transport == "streamable-http"


def test_default_host_and_port():
    args = _parse([])
    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_custom_host_and_port():
    args = _parse(["--host", "0.0.0.0", "--port", "9000"])
    assert args.host == "0.0.0.0"
    assert args.port == 9000


def test_allow_write_default_false():
    assert _parse([]).allow_write is False


def test_allow_write_flag():
    assert _parse(["--allow-write"]).allow_write is True


def test_api_key_default_is_none():
    assert _parse([]).api_key is None


def test_api_key_flag():
    assert _parse(["--api-key", "mysecret"]).api_key == "mysecret"


def test_refresh_specs_default_false():
    assert _parse([]).refresh_specs is False


def test_refresh_specs_flag():
    assert _parse(["--refresh-specs"]).refresh_specs is True


def test_offline_default_false():
    assert _parse([]).offline is False


def test_offline_flag():
    assert _parse(["--offline"]).offline is True


def test_invalid_transport_raises():
    with pytest.raises(SystemExit):
        _parse(["--transport", "sse"])


# --- BearerTokenMiddleware ---

async def _homepage(request):
    return PlainTextResponse("ok")


_inner_app = Starlette(routes=[Route("/", _homepage)])


def test_bearer_middleware_allows_valid_token():
    app = BearerTokenMiddleware(_inner_app, api_key="secret123")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Authorization": "Bearer secret123"})
    assert response.status_code == 200


def test_bearer_middleware_rejects_wrong_token():
    app = BearerTokenMiddleware(_inner_app, api_key="secret123")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Authorization": "Bearer wrongtoken"})
    assert response.status_code == 401


def test_bearer_middleware_rejects_missing_header():
    app = BearerTokenMiddleware(_inner_app, api_key="secret123")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/")
    assert response.status_code == 401


def test_bearer_middleware_rejects_malformed_header():
    app = BearerTokenMiddleware(_inner_app, api_key="secret123")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/", headers={"Authorization": "Basic secret123"})
    assert response.status_code == 401


def test_bearer_middleware_returns_www_authenticate_header():
    app = BearerTokenMiddleware(_inner_app, api_key="secret123")
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/")
    assert response.headers.get("WWW-Authenticate") == "Bearer"
