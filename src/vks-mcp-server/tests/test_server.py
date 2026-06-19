"""Tests for server CLI arg parsing and BearerTokenMiddleware."""

from __future__ import annotations

import argparse
import pytest
from greennode.vks_mcp_server.server import _build_parser
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient


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


def test_config_path_points_to_greenode_dir():
    """CONFIG_PATH must be the ~/.greenode directory (read by load_config), not a file."""
    from greennode.vks_mcp_server.server import CONFIG_PATH
    from pathlib import Path

    assert CONFIG_PATH == Path.home() / ".greenode"


from greennode.vks_mcp_server.server import create_server  # noqa: E402


def test_health_route_registered_on_http_app():
    app = create_server().streamable_http_app()
    paths = [getattr(r, "path", None) for r in app.router.routes]
    assert "/health" in paths


def test_health_endpoint_returns_200():
    app = create_server().streamable_http_app()
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def _health_ok(request):
    return PlainTextResponse("ok")


async def _mcp_stub(request):
    return PlainTextResponse("mcp")


_app_with_health = Starlette(routes=[Route("/health", _health_ok), Route("/mcp", _mcp_stub)])


def test_bearer_middleware_exempts_health():
    app = BearerTokenMiddleware(_app_with_health, api_key="secret123")
    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/health").status_code == 200
    assert client.get("/mcp").status_code == 401
    assert client.get("/mcp", headers={"Authorization": "Bearer secret123"}).status_code == 200


from greennode.vks_mcp_server.server import _resolve_auth  # noqa: E402


def _args(**kw):
    base = {
        "auth_mode": None,
        "api_key": None,
        "jwt_issuer": None,
        "jwt_jwks_uri": None,
        "jwt_audience": None,
        "jwt_required_scopes": None,
        "resource_url": None,
    }
    base.update(kw)
    return argparse.Namespace(**base)


def test_resolve_auth_defaults_to_none(monkeypatch):
    monkeypatch.delenv("GRN_MCP_AUTH_MODE", raising=False)
    mode, jwt_config, api_key = _resolve_auth(_args())
    assert mode == "none"
    assert jwt_config is None


def test_resolve_auth_api_key_from_env(monkeypatch):
    monkeypatch.setenv("GRN_MCP_API_KEY", "secret")
    mode, jwt_config, api_key = _resolve_auth(_args(auth_mode="api-key"))
    assert mode == "api-key"
    assert api_key == "secret"
    assert jwt_config is None


def test_resolve_auth_jwt_builds_config():
    a = _args(
        auth_mode="jwt",
        jwt_issuer="https://iam.example.com",
        jwt_jwks_uri="https://iam.example.com/jwks",
        jwt_audience="vks-mcp",
        resource_url="https://mcp.example.com/mcp",
        jwt_required_scopes="mcp:use, mcp:tools",
    )
    mode, jwt_config, _ = _resolve_auth(a)
    assert mode == "jwt"
    assert jwt_config is not None
    assert jwt_config.issuer == "https://iam.example.com"
    assert jwt_config.audience == "vks-mcp"
    assert jwt_config.required_scopes == ["mcp:use", "mcp:tools"]


def test_resolve_auth_jwt_missing_required_exits():
    a = _args(auth_mode="jwt", jwt_issuer="https://iam.example.com")  # missing jwks/aud/resource
    with pytest.raises(SystemExit):
        _resolve_auth(a)


def test_resolve_auth_api_key_missing_key_exits(monkeypatch):
    monkeypatch.delenv("GRN_MCP_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        _resolve_auth(_args(auth_mode="api-key"))


def _jwt_config():
    from greennode.vks_mcp_server.auth_verifier import JwtAuthConfig

    return JwtAuthConfig(
        issuer="https://iam.example.com",
        jwks_uri="https://iam.example.com/jwks",
        audience="vks-mcp",
        resource_url="https://mcp.example.com/mcp",
    )


def test_jwt_mode_protects_mcp_endpoint():
    app = create_server(_jwt_config()).streamable_http_app()
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/mcp")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_jwt_mode_health_still_open():
    app = create_server(_jwt_config()).streamable_http_app()
    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/health").status_code == 200


def test_no_auth_mode_mcp_not_401():
    app = create_server().streamable_http_app()
    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/mcp").status_code != 401
