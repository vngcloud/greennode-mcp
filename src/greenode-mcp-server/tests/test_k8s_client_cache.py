import pytest
import httpx
import respx
from unittest.mock import patch, MagicMock

from greennode.greenode_mcp_server.k8s_client_cache import K8sClientCache
from greennode.greenode_mcp_server.config import load_config
from greennode.greenode_mcp_server.auth import TokenManager
from greennode.greenode_mcp_server.client import GreenodeClient

VKS_BASE = "https://vks.api.vngcloud.vn"
IAM_URL = "https://iamapis.vngcloud.vn/accounts-api/v1/auth/token"

SAMPLE_KUBECONFIG_YAML = """apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: dGVzdC1jYS1kYXRh
    server: https://10.0.0.1:6443
  name: test-cluster
contexts:
- context:
    cluster: test-cluster
    user: admin
  name: admin@test-cluster
current-context: admin@test-cluster
kind: Config
users:
- name: admin
  user:
    client-certificate-data: dGVzdC1jZXJ0
    client-key-data: dGVzdC1rZXk=
"""


def _kubeconfig_response(status: str = "ACTIVE", yaml: str | None = None) -> dict:
    """Shape matches VKS `ClusterKubeConfigDto`."""
    return {
        "status": status,
        "kubeConfig": yaml if yaml is not None else SAMPLE_KUBECONFIG_YAML,
        "expirationAt": "2026-05-07T00:00:00.000Z",
        "expirationDays": 30,
        "renewalWarning": False,
    }


def _mock_iam():
    respx.post(IAM_URL).mock(return_value=httpx.Response(
        200,
        json={"accessToken": "t", "refreshToken": "r", "expiresIn": 1800, "refreshExpiresIn": 3600},
    ))


@respx.mock
@pytest.mark.asyncio
async def test_get_client_fetches_kubeconfig(sample_config):
    _mock_iam()
    respx.get(f"{VKS_BASE}/v1/clusters/k8s-123/kubeconfig").mock(
        return_value=httpx.Response(200, json=_kubeconfig_response()),
    )
    config = load_config(sample_config)
    tm = TokenManager(config)
    vks_client = GreenodeClient(config, tm)
    cache = K8sClientCache(vks_client)
    with patch("greennode.greenode_mcp_server.k8s_client_cache.K8sApis") as MockK8sApis:
        mock_instance = MagicMock()
        MockK8sApis.from_api_client.return_value = mock_instance
        client = await cache.get_client("k8s-123")
        assert client == mock_instance
        MockK8sApis.from_api_client.assert_called_once()


@respx.mock
@pytest.mark.asyncio
async def test_get_client_uses_cache(sample_config):
    _mock_iam()
    route = respx.get(f"{VKS_BASE}/v1/clusters/k8s-123/kubeconfig").mock(
        return_value=httpx.Response(200, json=_kubeconfig_response()),
    )
    config = load_config(sample_config)
    tm = TokenManager(config)
    vks_client = GreenodeClient(config, tm)
    cache = K8sClientCache(vks_client)
    with patch("greennode.greenode_mcp_server.k8s_client_cache.K8sApis") as MockK8sApis:
        mock_instance = MagicMock()
        MockK8sApis.from_api_client.return_value = mock_instance
        await cache.get_client("k8s-123")
        await cache.get_client("k8s-123")
        assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_get_client_raises_when_status_none(sample_config):
    _mock_iam()
    respx.get(f"{VKS_BASE}/v1/clusters/k8s-new/kubeconfig").mock(
        return_value=httpx.Response(200, json=_kubeconfig_response(status="NONE", yaml="")),
    )
    config = load_config(sample_config)
    cache = K8sClientCache(GreenodeClient(config, TokenManager(config)))
    with pytest.raises(RuntimeError, match="no kubeconfig yet"):
        await cache.get_client("k8s-new")


@respx.mock
@pytest.mark.asyncio
async def test_get_client_raises_when_status_creating(sample_config):
    _mock_iam()
    respx.get(f"{VKS_BASE}/v1/clusters/k8s-creating/kubeconfig").mock(
        return_value=httpx.Response(200, json=_kubeconfig_response(status="CREATING", yaml="")),
    )
    config = load_config(sample_config)
    cache = K8sClientCache(GreenodeClient(config, TokenManager(config)))
    with pytest.raises(RuntimeError, match="still being generated"):
        await cache.get_client("k8s-creating")


@respx.mock
@pytest.mark.asyncio
async def test_get_client_raises_when_kubeconfig_field_missing(sample_config):
    _mock_iam()
    respx.get(f"{VKS_BASE}/v1/clusters/k8s-weird/kubeconfig").mock(
        return_value=httpx.Response(200, json={"status": "ACTIVE"}),  # no kubeConfig key
    )
    config = load_config(sample_config)
    cache = K8sClientCache(GreenodeClient(config, TokenManager(config)))
    with pytest.raises(RuntimeError, match="no 'kubeConfig' field"):
        await cache.get_client("k8s-weird")
