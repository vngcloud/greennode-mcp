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


def _suggest_group(flavor: dict) -> str:
    """Classify a flavor into a deployment-need group."""
    cpu = float(flavor.get("cpu") or 0)
    memory = float(flavor.get("memory") or 0)
    gpu = float(flavor.get("gpu") or 0)
    if gpu > 0:
        return "AI/GPU"
    if cpu and memory / cpu >= 6:
        return "RAM cao"
    if cpu >= 8:
        return "Compute"
    if cpu <= 2:
        return "Dev/test"
    return "Cân bằng"


async def _flavor_list(
    config: VksConfig,
    client: VksClient,
    region: str | None = None,
    need: str | None = None,
) -> str:
    """Fetch cluster flavors, return a markdown table grouped by need."""
    pid = _require_project_id(config)
    data = await client.vserver_get(f"/v1/{pid}/flavors/customs/clusters", region=region)
    items = _as_list(data, "listData")
    rows = []
    n = 0
    for f in items:
        group = _suggest_group(f)
        if need and group.lower() != need.lower():
            continue
        n += 1
        rows.append(
            f"| {n} | {f.get('name', '')} | {f.get('flavorId', '')} | "
            f"{f.get('cpu', '')} | {f.get('memory', '')} | {f.get('gpu', '')} | {group} |"
        )
    empty = (
        f"No flavor found for need '{need}'."
        if need
        else "No flavor found in this project/region."
    )
    return _table(
        "Flavors:" + (f" (need: {need})" if need else ""),
        "| # | Name | ID | vCPU | RAM (GB) | GPU | Nhóm gợi ý |",
        "|---|---|---|---|---|---|---|",
        rows,
        empty,
    )


async def _sshkey_list(config: VksConfig, client: VksClient, region: str | None = None) -> str:
    """Fetch SSH keys, return a markdown table."""
    pid = _require_project_id(config)
    data = await client.vserver_get(
        f"/v2/{pid}/sshKeys", region=region, params={"page": 1, "size": 100}
    )
    items = _as_list(data, "listData")
    rows = [
        f"| {i} | {k.get('name', '')} | {k.get('id', '')} |" for i, k in enumerate(items, start=1)
    ]
    return _table(
        "SSH keys:",
        "| # | Name | ID |",
        "|---|---|---|",
        rows,
        "No SSH key found. Create one in the VNG Cloud console first.",
    )


async def _secgroup_list(config: VksConfig, client: VksClient, region: str | None = None) -> str:
    """Fetch security groups, return a markdown table."""
    pid = _require_project_id(config)
    data = await client.vserver_get(f"/v2/{pid}/secgroups", region=region)
    items = _as_list(data, "listData")
    rows = [
        f"| {i} | {g.get('name', '')} | {g.get('id', '')} | "
        f"{g.get('description', '')} | {g.get('status', '')} |"
        for i, g in enumerate(items, start=1)
    ]
    return _table(
        "Security groups:",
        "| # | Name | ID | Description | Status |",
        "|---|---|---|---|---|",
        rows,
        "No security group found in this project/region.",
    )


class DiscoveryHandler:
    """Register and serve read-only vServer resource-discovery MCP tools."""

    def __init__(self, mcp, config: VksConfig, client: VksClient):
        self.mcp = mcp
        self.config = config
        self.client = client

        self.mcp.tool(name="vpc_list")(self.vpc_list)
        self.mcp.tool(name="subnet_list")(self.subnet_list)
        self.mcp.tool(name="flavor_list")(self.flavor_list)
        self.mcp.tool(name="sshkey_list")(self.sshkey_list)
        self.mcp.tool(name="secgroup_list")(self.secgroup_list)

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

    async def flavor_list(
        self,
        need: str | None = Field(
            None,
            description="Filter by deployment need group: Dev/test, Cân bằng, Compute, RAM cao, AI/GPU",
        ),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """List cluster flavors with a suggested deployment-need group. Use the ID as `flavorId`."""
        return await _flavor_list(self.config, self.client, region=region, need=need)

    async def sshkey_list(
        self,
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """List SSH keys in the project. Use the ID as `sshKeyId` when creating a node group."""
        return await _sshkey_list(self.config, self.client, region=region)

    async def secgroup_list(
        self,
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """List security groups. Use IDs in `securityGroups` when creating a node group."""
        return await _secgroup_list(self.config, self.client, region=region)
