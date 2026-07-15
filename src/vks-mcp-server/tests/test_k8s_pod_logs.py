"""get_pod_logs edge cases (the kubernetes client is faked at the cache layer)."""

from __future__ import annotations

import pytest
from greennode.vks_mcp_server.auth import TokenManager
from greennode.vks_mcp_server.client import VksClient
from greennode.vks_mcp_server.config import load_config
from greennode.vks_mcp_server.k8s_handler import K8sHandler
from mcp.server.fastmcp import FastMCP


class _FakeK8sApis:
    def __init__(self, logs):
        self._logs = logs

    def get_pod_logs(self, **kwargs):
        return self._logs


@pytest.fixture
def handler(sample_config):
    config = load_config(sample_config)
    client = VksClient(config, TokenManager(config))
    return K8sHandler(
        FastMCP("t"), config, client, allow_write=False, allow_sensitive_data_access=True
    )


@pytest.mark.asyncio
async def test_get_pod_logs_handles_none_logs(handler, monkeypatch):
    """A pod with no logs yet (Pending / container not started) returns None
    from the kubernetes client — the tool must report 'no logs', not crash
    with 'NoneType' object has no attribute 'splitlines' (QC finding)."""

    async def fake_get_client(cluster_id, region=None):
        return _FakeK8sApis(logs=None)

    monkeypatch.setattr(handler, "get_client", fake_get_client)
    result = await handler.get_pod_logs(
        cluster_id="k8s-abc",
        pod_name="cilium-operator-x",
        namespace="kube-system",
        container_name=None,
        since_seconds=None,
        tail_lines=None,
        limit_bytes=None,
        previous=False,
        region=None,
    )
    assert result.log_lines == []


@pytest.mark.asyncio
async def test_get_pod_logs_happy_path(handler, monkeypatch):
    async def fake_get_client(cluster_id, region=None):
        return _FakeK8sApis(logs="line1\nline2")

    monkeypatch.setattr(handler, "get_client", fake_get_client)
    result = await handler.get_pod_logs(
        cluster_id="k8s-abc",
        pod_name="coredns-x",
        namespace="kube-system",
        container_name=None,
        since_seconds=None,
        tail_lines=None,
        limit_bytes=None,
        previous=False,
        region=None,
    )
    assert result.log_lines == ["line1", "line2"]
