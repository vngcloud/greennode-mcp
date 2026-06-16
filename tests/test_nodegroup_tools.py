"""Tests for node group tools."""
from __future__ import annotations

import pytest
import respx
import httpx

from vks_mcp_server.config import load_config
from vks_mcp_server.auth import TokenManager
from vks_mcp_server.client import VksClient
from vks_mcp_server.nodegroup_handler import _nodegroup_list, _nodegroup_delete_dryrun

VKS_BASE = "https://vks.api.vngcloud.vn"
IAM_URL = "https://iamapis.vngcloud.vn/accounts-api/v1/auth/token"


def _mock_iam(mock: respx.MockRouter) -> None:
    """Register a mock IAM token response."""
    mock.post(IAM_URL).mock(return_value=httpx.Response(
        200, json={"accessToken": "mocked-token", "expiresIn": 1800},
    ))


@pytest.fixture
def config(sample_config):
    return load_config(sample_config)


@pytest.fixture
def client(config):
    token_manager = TokenManager(config)
    return VksClient(config, token_manager)


@respx.mock
@pytest.mark.asyncio
async def test_nodegroup_list(config, client):
    """nodegroup_list fetches node groups and cluster name, returns table."""
    _mock_iam(respx.mock)
    cluster_id = "cluster-abc123"
    ng_items = [
        {
            "name": "ng-default", "uid": "ng-uid-001", "status": "ACTIVE",
            "nodeCount": 3, "imageId": "img-001", "createdAt": "2024-01-15T10:00:00Z",
        },
        {
            "name": "ng-worker", "uid": "ng-uid-002", "status": "ACTIVE",
            "nodeCount": 5, "imageId": "img-002", "createdAt": "2024-01-16T12:00:00Z",
        },
    ]
    cluster_data = {"name": "my-cluster", "uid": cluster_id, "status": "ACTIVE"}
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}/node-groups").mock(
        return_value=httpx.Response(200, json=ng_items),
    )
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}").mock(
        return_value=httpx.Response(200, json=cluster_data),
    )
    result = await _nodegroup_list(config, client, cluster_id=cluster_id)
    assert "ng-default" in result
    assert "ng-worker" in result
    assert "my-cluster" in result


@respx.mock
@pytest.mark.asyncio
async def test_nodegroup_list_with_region(config, client):
    """nodegroup_list passes region parameter correctly."""
    _mock_iam(respx.mock)
    cluster_id = "cluster-xyz"
    ng_items = [{
        "name": "ng-han", "uid": "ng-han-001", "status": "ACTIVE",
        "nodeCount": 2, "imageId": "img-han", "createdAt": "2024-02-01T00:00:00Z",
    }]
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}/node-groups").mock(
        return_value=httpx.Response(200, json=ng_items),
    )
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}").mock(
        return_value=httpx.Response(200, json={"name": "han-cluster", "uid": cluster_id}),
    )
    result = await _nodegroup_list(config, client, cluster_id=cluster_id, region="HCM-3")
    assert "ng-han" in result


@respx.mock
@pytest.mark.asyncio
async def test_nodegroup_list_cluster_fetch_fails(config, client):
    """nodegroup_list still works when cluster GET fails (falls back to cluster_id)."""
    _mock_iam(respx.mock)
    cluster_id = "cluster-fallback"
    ng_items = [{
        "name": "ng-one", "uid": "ng-one-001", "status": "ACTIVE",
        "nodeCount": 1, "imageId": "img-x", "createdAt": "2024-03-01T00:00:00Z",
    }]
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}/node-groups").mock(
        return_value=httpx.Response(200, json=ng_items),
    )
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}").mock(
        return_value=httpx.Response(404, json={"message": "not found"}),
    )
    result = await _nodegroup_list(config, client, cluster_id=cluster_id)
    assert "ng-one" in result
    assert cluster_id in result


@respx.mock
@pytest.mark.asyncio
async def test_nodegroup_list_empty(config, client):
    """nodegroup_list returns empty message when no node groups."""
    _mock_iam(respx.mock)
    cluster_id = "cluster-empty"
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}/node-groups").mock(
        return_value=httpx.Response(200, json=[]),
    )
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}").mock(
        return_value=httpx.Response(200, json={"name": "empty-cluster", "uid": cluster_id}),
    )
    result = await _nodegroup_list(config, client, cluster_id=cluster_id)
    assert "No node groups found" in result


@respx.mock
@pytest.mark.asyncio
async def test_nodegroup_delete_dryrun(config, client):
    """nodegroup_delete_dryrun returns warning with YOU ARE ABOUT TO DELETE NODE GROUP."""
    _mock_iam(respx.mock)
    cluster_id = "cluster-abc123"
    nodegroup_id = "ng-uid-001"
    ng_detail = {
        "name": "ng-default", "uid": "ng-uid-001", "status": "ACTIVE",
        "nodeCount": 3, "imageId": "img-001", "createdAt": "2024-01-15T10:00:00Z",
    }
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}/node-groups/{nodegroup_id}").mock(
        return_value=httpx.Response(200, json=ng_detail),
    )
    result = await _nodegroup_delete_dryrun(
        config, client, cluster_id=cluster_id, nodegroup_id=nodegroup_id,
    )
    assert "YOU ARE ABOUT TO DELETE NODE GROUP" in result
    assert nodegroup_id in result
    assert cluster_id in result
    assert "IRREVERSIBLE" in result


@respx.mock
@pytest.mark.asyncio
async def test_nodegroup_delete_dryrun_includes_node_count(config, client):
    """nodegroup_delete_dryrun warning includes node count."""
    _mock_iam(respx.mock)
    cluster_id = "cluster-prod"
    nodegroup_id = "ng-prod-001"
    ng_detail = {
        "name": "ng-production", "uid": "ng-prod-001", "status": "ACTIVE",
        "nodeCount": 10, "imageId": "img-prod", "createdAt": "2024-01-01T00:00:00Z",
    }
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}/node-groups/{nodegroup_id}").mock(
        return_value=httpx.Response(200, json=ng_detail),
    )
    result = await _nodegroup_delete_dryrun(
        config, client, cluster_id=cluster_id, nodegroup_id=nodegroup_id,
    )
    assert "10" in result
    assert "nodegroup_delete" in result
