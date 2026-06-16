"""Tests for version and image tools."""
from __future__ import annotations

import pytest
import respx
import httpx

from vks_mcp_server.config import load_config
from vks_mcp_server.auth import TokenManager
from vks_mcp_server.client import VksClient
from vks_mcp_server.version_handler import _cluster_versions_list, _nodegroup_images_list

VKS_BASE = "https://vks.api.vngcloud.vn"
IAM_URL = "https://iamapis.vngcloud.vn/accounts-api/v1/auth/token"


def _mock_iam(mock: respx.MockRouter) -> None:
    mock.post(IAM_URL).mock(return_value=httpx.Response(
        200, json={"accessToken": "mocked-token", "expiresIn": 1800},
    ))


@pytest.fixture
def config_and_client(sample_config):
    config = load_config(sample_config)
    token_manager = TokenManager(config)
    client = VksClient(config, token_manager)
    return config, client


CLUSTER_VERSIONS_RESPONSE = {
    "items": [
        {"version": "v1.29.0", "stage": "STABLE", "deprecatedAt": None, "enable": True},
        {"version": "v1.28.0", "stage": "STABLE", "deprecatedAt": "2024-06-01", "enable": True},
        {"version": "v1.27.0", "stage": "STABLE", "deprecatedAt": None, "enable": False},
    ]
}

NODE_GROUP_IMAGES_RESPONSE = {
    "items": [
        {"id": "img-abc123", "os": "Ubuntu 22.04", "kubernetesVersion": "v1.29.0", "stage": "STABLE", "enable": True},
        {"id": "img-disabled", "os": "Ubuntu 20.04", "kubernetesVersion": "v1.28.0", "stage": "STABLE", "enable": False},
    ]
}


@respx.mock
@pytest.mark.asyncio
async def test_cluster_versions_list(config_and_client):
    """Enabled versions appear; disabled versions do not; recommendation is marked."""
    config, client = config_and_client
    _mock_iam(respx.mock)
    respx.get(f"{VKS_BASE}/v1/cluster-versions").mock(
        return_value=httpx.Response(200, json=CLUSTER_VERSIONS_RESPONSE),
    )
    result = await _cluster_versions_list(config, client, region=None)
    assert len(result) == 1
    text = result[0].text
    assert "v1.29.0" in text
    assert "v1.28.0" in text
    assert "v1.27.0" not in text
    assert "recommended" in text.lower()


@respx.mock
@pytest.mark.asyncio
async def test_nodegroup_images_list(config_and_client):
    """Enabled images appear; disabled images do not."""
    config, client = config_and_client
    _mock_iam(respx.mock)
    respx.get(f"{VKS_BASE}/v1/node-group-images").mock(
        return_value=httpx.Response(200, json=NODE_GROUP_IMAGES_RESPONSE),
    )
    result = await _nodegroup_images_list(config, client, region=None)
    assert len(result) == 1
    text = result[0].text
    assert "img-abc123" in text
    assert "Ubuntu 22.04" in text
    assert "img-disabled" not in text
    assert "Ubuntu 20.04" not in text
