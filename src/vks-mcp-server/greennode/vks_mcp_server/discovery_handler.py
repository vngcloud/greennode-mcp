"""Resource discovery handler for GreenNode MCP Server (vServer reads)."""

from __future__ import annotations

from greennode.vks_mcp_server.client import VksClient
from greennode.vks_mcp_server.config import VksConfig
from greennode.vks_mcp_server.validators import validate_id
from pydantic import Field


def _require_project_id(config: VksConfig) -> str:
    """Return the configured project_id or raise a clear error."""
    if not config.project_id:
        raise ValueError(
            "project_id is not configured. Run 'grn configure' or set GRN_PROJECT_ID."
        )
    return config.project_id


def _as_list(data, *wrapper_keys):
    """Normalise a vServer response to a list.

    Accepts a bare array, or a dict wrapping the array under one of
    *wrapper_keys* (e.g. 'listData').
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in wrapper_keys:
            if isinstance(data.get(key), list):
                return data[key]
    return []


def _table(title: str, header: str, sep: str, rows: list[str], empty: str) -> str:
    """Assemble a markdown table, or return *empty* when there are no rows."""
    if not rows:
        return empty
    return f"{title}\n\n" + "\n".join([header, sep] + rows)


async def _vpc_list(config: VksConfig, client: VksClient, region: str | None = None) -> str:
    """Fetch VPCs/networks, return a markdown table."""
    pid = _require_project_id(config)
    data = await client.vserver_get(f"/v2/{pid}/networks", region=region)
    items = _as_list(data, "listData")
    rows = []
    for i, v in enumerate(items, start=1):
        rows.append(
            f"| {i} | {v.get('displayName', '')} | {v.get('id', '')} | "
            f"{v.get('cidr', '')} | {v.get('status', '')} |"
        )
    return _table(
        "VPCs (networks):",
        "| # | Name | ID | CIDR | Status |",
        "|---|---|---|---|---|",
        rows,
        "No VPC found in this project/region.",
    )


async def _subnet_list(
    config: VksConfig, client: VksClient, vpc_id: str, region: str | None = None
) -> str:
    """Fetch subnets of a VPC, return a markdown table."""
    validate_id(vpc_id, "vpc_id")
    pid = _require_project_id(config)
    data = await client.vserver_get(f"/v2/{pid}/networks/{vpc_id}/subnets", region=region)
    items = _as_list(data, "listData")
    rows = []
    for i, s in enumerate(items, start=1):
        rows.append(
            f"| {i} | {s.get('name', '')} | {s.get('uuid', '')} | "
            f"{s.get('cidr', '')} | {s.get('status', '')} |"
        )
    return _table(
        f"Subnets (vpc: {vpc_id}):",
        "| # | Name | ID | CIDR | Status |",
        "|---|---|---|---|---|",
        rows,
        "No subnet found in this VPC.",
    )


class DiscoveryHandler:
    """Register and serve read-only vServer resource-discovery MCP tools."""

    def __init__(self, mcp, config: VksConfig, client: VksClient):
        self.mcp = mcp
        self.config = config
        self.client = client

        self.mcp.tool(name="vpc_list")(self.vpc_list)
        self.mcp.tool(name="subnet_list")(self.subnet_list)

    async def vpc_list(
        self,
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """List VPCs (networks) in the project. Use the ID as `vpcId` when creating a cluster."""
        return await _vpc_list(self.config, self.client, region=region)

    async def subnet_list(
        self,
        vpc_id: str = Field(..., description="VPC/network ID (from vpc_list)"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """List subnets of a VPC. Use the ID as `subnetId` when creating a cluster."""
        return await _subnet_list(self.config, self.client, vpc_id=vpc_id, region=region)
