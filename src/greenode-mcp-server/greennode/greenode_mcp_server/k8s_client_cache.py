"""Kubernetes client cache for GreenNode MCP Server.

Manages K8s API clients per cluster with TTL-based caching.
Fetches kubeconfig from VKS API and creates kubernetes clients.
"""
from __future__ import annotations

import yaml
from cachetools import TTLCache

from greennode.greenode_mcp_server.client import GreenodeClient
from greennode.greenode_mcp_server.k8s_apis import K8sApis

# 14 minutes TTL — kubeconfig tokens typically last 15m
CLIENT_TTL = 840


class K8sClientCache:
    """Cache for Kubernetes API clients keyed by VKS cluster ID."""

    def __init__(self, vks_client: GreenodeClient) -> None:
        self._vks_client = vks_client
        self._cache = TTLCache(maxsize=100, ttl=CLIENT_TTL)

    async def get_client(self, cluster_id: str, region: str | None = None) -> K8sApis:
        """Get a K8sApis client for the given cluster.

        Fetches kubeconfig from VKS API on cache miss, creates a
        kubernetes client, and caches it with TTL.
        """
        if cluster_id not in self._cache:
            self._cache[cluster_id] = await self._create_client(cluster_id, region)
        return self._cache[cluster_id]

    async def _create_client(self, cluster_id: str, region: str | None) -> K8sApis:
        """Fetch kubeconfig from VKS API and create a K8sApis instance.

        VKS returns `ClusterKubeConfigDto`:
            {"kubeConfig": "<yaml>", "status": "ACTIVE" | "NONE" | "CREATING" | "ERROR", ...}

        We extract `kubeConfig` (the YAML string) and only use it when status
        is ACTIVE. For NONE/CREATING/ERROR we raise a clear error so the
        caller knows to request kubeconfig creation first.
        """
        from kubernetes import config as k8s_config

        response = await self._vks_client.get(
            f"/v1/clusters/{cluster_id}/kubeconfig",
            region=region,
        )

        status = response.get("status")
        if status == "NONE":
            raise RuntimeError(
                f"Cluster {cluster_id} has no kubeconfig yet. "
                f"Create one via POST /v1/clusters/{cluster_id}/kubeconfig first."
            )
        if status == "CREATING":
            raise RuntimeError(
                f"Kubeconfig for cluster {cluster_id} is still being generated. Try again shortly."
            )
        if status == "ERROR":
            raise RuntimeError(f"Kubeconfig for cluster {cluster_id} is in ERROR state.")

        kubeconfig_yaml = response.get("kubeConfig")
        if not kubeconfig_yaml:
            raise RuntimeError(
                f"Kubeconfig response for cluster {cluster_id} had no 'kubeConfig' field. "
                f"Response keys: {sorted(response.keys())}"
            )

        kubeconfig_dict = yaml.safe_load(kubeconfig_yaml)
        api_client = k8s_config.new_client_from_config_dict(kubeconfig_dict)
        return K8sApis.from_api_client(api_client)
