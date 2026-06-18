"""Version and image handler for GreenNode MCP Server."""

from __future__ import annotations

from greennode.vks_mcp_server.client import VksClient
from greennode.vks_mcp_server.config import VksConfig
from mcp import types
from pydantic import Field


# ---------------------------------------------------------------------------
# Internal implementation functions
# ---------------------------------------------------------------------------


async def _cluster_versions_list(
    config: VksConfig,
    client: VksClient,
    region: str | None = None,
) -> list[types.TextContent]:
    """Fetch and format available Kubernetes cluster versions."""
    data = await client.get("/v1/cluster-versions", region=region)
    items = data.get("items", data) if isinstance(data, list) else data
    if isinstance(items, dict):
        items = items.get("items", items)

    # Filter enabled versions only
    items = [v for v in items if v.get("enable", True)]

    # Find stable versions for the "recommended" marker
    stable_versions = [
        v for v in items if v.get("stage", "").upper() == "STABLE" and not v.get("deprecatedAt")
    ]
    stable_versions.sort(key=lambda v: v.get("version", ""), reverse=True)
    recommended_name = stable_versions[0].get("version", "") if stable_versions else ""

    lines = [
        "Available Kubernetes versions:",
        "",
        "| # | Version | Stage | Deprecated At | Note |",
        "|---|---------|-------|---------------|---------|",
    ]

    for idx, v in enumerate(items, start=1):
        name = v.get("version", "")
        stage = v.get("stage", "")
        deprecated_at = v.get("deprecatedAt", "")
        note = "Recommended" if name == recommended_name else ""
        lines.append(f"| {idx} | {name} | {stage} | {deprecated_at} | {note} |")

    return [types.TextContent(type="text", text="\n".join(lines))]


# ---------------------------------------------------------------------------
# VersionHandler class
# ---------------------------------------------------------------------------


class VersionHandler:
    """Register and serve Kubernetes version-listing MCP tools."""

    def __init__(self, mcp, config: VksConfig, client: VksClient):
        self.mcp = mcp
        self.config = config
        self.client = client

        self.mcp.tool(name="cluster_versions_list")(self.cluster_versions_list)

    async def cluster_versions_list(
        self,
        region: str | None = Field(None, description="Region override (default: config region)"),
    ) -> str:
        """List available Kubernetes versions for VKS clusters.

        Only shows enabled versions and marks the latest stable non-deprecated
        version as recommended. Call this before cluster_create to choose a
        valid version and releaseChannel.
        """
        result = await _cluster_versions_list(self.config, self.client, region)
        return result[0].text
