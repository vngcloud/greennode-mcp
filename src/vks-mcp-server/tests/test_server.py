"""Tests for server CLI arg parsing and BearerTokenMiddleware."""
from __future__ import annotations

import argparse

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from greennode.vks_mcp_server.server import _build_parser


def _parse_args(argv: list[str]) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def test_default_transport_is_stdio():
    args = _parse_args([])
    assert args.transport == "stdio"


def test_transport_http_flag():
    args = _parse_args(["--transport", "streamable-http"])
    assert args.transport == "streamable-http"


def test_default_host_and_port():
    args = _parse_args(["--transport", "streamable-http"])
    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_custom_host_and_port():
    args = _parse_args(["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9000"])
    assert args.host == "0.0.0.0"
    assert args.port == 9000


def test_api_key_default_is_none():
    args = _parse_args([])
    assert args.api_key is None


def test_api_key_flag():
    args = _parse_args(["--api-key", "mysecrettoken"])
    assert args.api_key == "mysecrettoken"


def test_invalid_transport_raises():
    with pytest.raises(SystemExit):
        _parse_args(["--transport", "sse"])


from greennode.vks_mcp_server.server import BearerTokenMiddleware  # noqa: E402


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
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "Bearer"
