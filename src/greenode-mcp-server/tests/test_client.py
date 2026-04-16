"""Tests for GreenodeClient HTTP client."""
from __future__ import annotations

import pytest
import respx
import httpx

from greennode.greenode_mcp_server.config import load_config
from greennode.greenode_mcp_server.auth import TokenManager
from greennode.greenode_mcp_server.client import GreenodeClient

VKS_BASE = "https://vks.api.vngcloud.vn"
IAM_URL = "https://iamapis.vngcloud.vn/accounts-api/v1/auth/token"


def _mock_iam(mock: respx.MockRouter) -> None:
    """Register a mock IAM token response."""
    mock.post(IAM_URL).mock(return_value=httpx.Response(
        200, json={"accessToken": "mocked-token", "expiresIn": 1800},
    ))


@pytest.fixture
def client(sample_config):
    config = load_config(sample_config)
    token_manager = TokenManager(config)
    return GreenodeClient(config, token_manager)


@respx.mock
@pytest.mark.asyncio
async def test_client_get(client):
    """GET /v1/clusters returns parsed JSON."""
    _mock_iam(respx.mock)
    expected = {"items": [{"name": "cluster-1"}]}
    respx.get(f"{VKS_BASE}/v1/clusters").mock(return_value=httpx.Response(200, json=expected))
    result = await client.get("/v1/clusters")
    assert result == expected


@respx.mock
@pytest.mark.asyncio
async def test_client_post(client):
    """POST /v1/clusters with query params returns parsed JSON."""
    _mock_iam(respx.mock)
    payload = {"name": "new-cluster"}
    created = {"id": "abc123", "name": "new-cluster"}
    respx.post(f"{VKS_BASE}/v1/clusters").mock(
        return_value=httpx.Response(201, json=created),
    )
    result = await client.post(
        "/v1/clusters",
        params={"poc": "false", "autoRenewal": "true"},
        json=payload,
    )
    assert result == created


@respx.mock
@pytest.mark.asyncio
async def test_client_auto_retry_on_401(client):
    """On 401, client refreshes token and retries; second call succeeds."""
    _mock_iam(respx.mock)
    success_body = {"items": []}
    route = respx.get(f"{VKS_BASE}/v1/clusters").mock(
        side_effect=[
            httpx.Response(401, json={"message": "Unauthorized"}),
            httpx.Response(200, json=success_body),
        ]
    )
    result = await client.get("/v1/clusters")
    assert result == success_body
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_client_raises_on_404(client):
    """404 response raises RuntimeError containing 'not found'."""
    _mock_iam(respx.mock)
    respx.get(f"{VKS_BASE}/v1/clusters/missing").mock(
        return_value=httpx.Response(404, json={"message": "cluster not found"}),
    )
    with pytest.raises(RuntimeError, match="not found"):
        await client.get("/v1/clusters/missing")
