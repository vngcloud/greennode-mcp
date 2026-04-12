"""Cluster management handler for GreenNode MCP Server."""
from __future__ import annotations

import re
from typing import Any

from mcp import types
from pydantic import Field

from greennode.vks_mcp_server.client import VksClient
from greennode.vks_mcp_server.config import VksConfig
from greennode.vks_mcp_server.models import format_cluster_detail, format_cluster_table
from greennode.vks_mcp_server.validators import validate_id


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_CLUSTER_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{3,18}[a-z0-9]$")
_NODEGROUP_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{3,13}[a-z0-9]$")

_NETWORK_NEEDS_CIDR = {"CALICO", "CILIUM_OVERLAY"}
_NETWORK_NEEDS_SECONDARY_SUBNETS = {"CILIUM_NATIVE_ROUTING"}

_REQUIRED_CLUSTER_FIELDS = ["vpcId", "networkType", "version", "releaseChannel"]
_REQUIRED_NODEGROUP_FIELDS = [
    "imageId", "flavorId", "diskSize", "diskType",
    "securityGroups", "sshKeyId", "upgradeConfig",
]


# ---------------------------------------------------------------------------
# Internal implementation functions
# ---------------------------------------------------------------------------

# These accept (client, arguments) and return list[types.TextContent].
# The ClusterHandler methods delegate to these after building an arguments dict.


async def _cluster_list(
    client: VksClient,
    arguments: dict,
) -> list[types.TextContent]:
    params = {}
    if "page" in arguments:
        params["page"] = arguments["page"]
    if "pageSize" in arguments:
        params["pageSize"] = arguments["pageSize"]
    region = arguments.get("region")

    data = await client.get("/v1/clusters", region=region, params=params or None)
    items = data.get("items", data) if isinstance(data, dict) else data
    resolved_region = region or client._config.default_region
    text = format_cluster_table(items, resolved_region)
    return [types.TextContent(type="text", text=text)]


async def _cluster_get(
    client: VksClient,
    arguments: dict,
) -> list[types.TextContent]:
    cluster_id = arguments["cluster_id"]
    validate_id(cluster_id, "cluster_id")
    region = arguments.get("region")
    data = await client.get(f"/v1/clusters/{cluster_id}", region=region)
    text = format_cluster_detail(data)
    return [types.TextContent(type="text", text=text)]


async def _cluster_create(
    client: VksClient,
    arguments: dict,
) -> list[types.TextContent]:
    body = arguments["body"]
    poc = arguments.get("poc", False)
    auto_renewal = arguments.get("autoRenewal", True)
    region = arguments.get("region")
    params = {"poc": str(poc).lower(), "autoRenewal": str(auto_renewal).lower()}
    data = await client.post("/v1/clusters", region=region, params=params, json=body)
    name = data.get("name", data.get("uid", ""))
    text = f"Cluster **{name}** created successfully.\n" + format_cluster_detail(data)
    return [types.TextContent(type="text", text=text)]


async def _cluster_update(
    client: VksClient,
    arguments: dict,
) -> list[types.TextContent]:
    cluster_id = arguments["cluster_id"]
    validate_id(cluster_id, "cluster_id")
    body = arguments["body"]
    region = arguments.get("region")
    data = await client.put(f"/v1/clusters/{cluster_id}", region=region, json=body)
    text = f"Cluster `{cluster_id}` updated successfully.\n" + format_cluster_detail(data)
    return [types.TextContent(type="text", text=text)]


async def _cluster_delete(
    client: VksClient,
    arguments: dict,
) -> list[types.TextContent]:
    cluster_id = arguments["cluster_id"]
    validate_id(cluster_id, "cluster_id")
    region = arguments.get("region")
    await client.delete(f"/v1/clusters/{cluster_id}", region=region)
    text = f"Cluster `{cluster_id}` deleted successfully."
    return [types.TextContent(type="text", text=text)]


async def _cluster_get_kubeconfig(
    client: VksClient,
    arguments: dict,
) -> list[types.TextContent]:
    cluster_id = arguments["cluster_id"]
    validate_id(cluster_id, "cluster_id")
    region = arguments.get("region")
    yaml_text = await client.get_raw(
        f"/v1/clusters/{cluster_id}/kubeconfig", region=region
    )
    return [types.TextContent(type="text", text=yaml_text)]


async def _cluster_get_events(
    client: VksClient,
    arguments: dict,
) -> list[types.TextContent]:
    cluster_id = arguments["cluster_id"]
    validate_id(cluster_id, "cluster_id")
    region = arguments.get("region")
    params = {}
    if "page" in arguments:
        params["page"] = arguments["page"]
    if "pageSize" in arguments:
        params["pageSize"] = arguments["pageSize"]

    data = await client.get(
        f"/v1/clusters/{cluster_id}/events",
        region=region,
        params=params or None,
    )

    items = data.get("items", data) if isinstance(data, dict) else data
    if not items:
        text = f"No events found for cluster `{cluster_id}`."
        return [types.TextContent(type="text", text=text)]

    header = f"Events for cluster `{cluster_id}`:"
    table_header = "| # | Type | Reason | Message | Timestamp |"
    separator = "|---|---|---|---|---|"
    rows = []
    for i, ev in enumerate(items, start=1):
        ev_type = ev.get("type", "")
        reason = ev.get("reason", "")
        message = ev.get("message", "")
        ts = str(ev.get("lastTimestamp", ev.get("eventTime", ev.get("createdAt", ""))))[:19]
        rows.append(f"| {i} | {ev_type} | {reason} | {message} | {ts} |")

    text = "\n".join([header, table_header, separator] + rows)
    return [types.TextContent(type="text", text=text)]


async def _cluster_auto_upgrade_config(
    client: VksClient,
    arguments: dict,
) -> list[types.TextContent]:
    cluster_id = arguments["cluster_id"]
    validate_id(cluster_id, "cluster_id")
    region = arguments.get("region")
    body = {"weekdays": arguments["weekdays"], "time": arguments["time"]}
    data = await client.put(
        f"/v1/clusters/{cluster_id}/auto-upgrade-config",
        region=region, json=body,
    )
    text = f"Auto-upgrade configuration for cluster `{cluster_id}` updated successfully.\n{data}"
    return [types.TextContent(type="text", text=text)]


async def _cluster_auto_upgrade_delete(
    client: VksClient,
    arguments: dict,
) -> list[types.TextContent]:
    cluster_id = arguments["cluster_id"]
    validate_id(cluster_id, "cluster_id")
    region = arguments.get("region")
    await client.delete(
        f"/v1/clusters/{cluster_id}/auto-upgrade-config",
        region=region,
    )
    text = f"Auto-upgrade configuration for cluster `{cluster_id}` deleted successfully."
    return [types.TextContent(type="text", text=text)]


async def _cluster_delete_dryrun(
    client: VksClient,
    arguments: dict,
) -> list[types.TextContent]:
    cluster_id = arguments["cluster_id"]
    validate_id(cluster_id, "cluster_id")
    region = arguments.get("region")

    cluster = await client.get(f"/v1/clusters/{cluster_id}", region=region)
    ng_data = await client.get(
        f"/v1/clusters/{cluster_id}/node-groups", region=region
    )

    node_groups = ng_data.get("items", ng_data) if isinstance(ng_data, dict) else ng_data

    cluster_name = cluster.get("name", cluster_id)
    cluster_status = cluster.get("status", "")
    cluster_version = cluster.get("version", cluster.get("kubernetesVersion", ""))
    node_count = cluster.get("nodeCount", cluster.get("numNodes", ""))

    lines = [
        f"WARNING: YOU ARE ABOUT TO DELETE CLUSTER: **{cluster_name}**",
        "",
        "| Property | Value |",
        "|---|---|",
        f"| ID | {cluster_id} |",
        f"| Name | {cluster_name} |",
        f"| Status | {cluster_status} |",
        f"| Version | {cluster_version} |",
        f"| Node count | {node_count} |",
        "",
        f"**Node groups to be deleted ({len(node_groups)}):**",
        "",
        "| # | Name | ID | Node count |",
        "|---|---|---|---|",
    ]

    for i, ng in enumerate(node_groups, start=1):
        ng_name = ng.get("name", "")
        ng_id = ng.get("uid", ng.get("id", ""))
        ng_nodes = ng.get("nodeCount", ng.get("numNodes", ""))
        lines.append(f"| {i} | {ng_name} | {ng_id} | {ng_nodes} |")

    lines += ["", "**This action is irreversible. Confirm by calling `cluster_delete`.**"]

    text = "\n".join(lines)
    return [types.TextContent(type="text", text=text)]


def _cluster_create_validate(
    arguments: dict,
) -> list[types.TextContent]:
    body = arguments.get("body", arguments)
    errors = []

    # Validate cluster name
    name = body.get("name", "")
    if not _CLUSTER_NAME_RE.match(name):
        errors.append(
            f"Cluster name '{name}' is invalid. "
            "Must match ^[a-z0-9][a-z0-9\\-]{{3,18}}[a-z0-9]$"
        )

    # Check required fields
    for field in _REQUIRED_CLUSTER_FIELDS:
        if not body.get(field):
            errors.append(f"Missing required field: {field}")

    # Check network-type-specific fields
    network_type = body.get("networkType", "")
    if network_type in _NETWORK_NEEDS_CIDR:
        if not body.get("cidr"):
            errors.append(f"networkType={network_type} requires 'cidr' field.")

    if network_type in _NETWORK_NEEDS_SECONDARY_SUBNETS:
        if not body.get("secondarySubnets"):
            errors.append(f"networkType={network_type} requires 'secondarySubnets' field.")

    # Validate node groups
    node_groups = body.get("nodeGroups", [])
    for idx, ng in enumerate(node_groups):
        prefix = f"nodeGroups[{idx}]"

        ng_name = ng.get("name", "")
        if not _NODEGROUP_NAME_RE.match(ng_name):
            errors.append(
                f"{prefix} name '{ng_name}' is invalid. "
                "Must match ^[a-z0-9][a-z0-9-]{{3,13}}[a-z0-9]$"
            )

        for field in _REQUIRED_NODEGROUP_FIELDS:
            if ng.get(field) is None or ng.get(field) == "" or ng.get(field) == []:
                errors.append(f"{prefix}: Missing required field: {field}")

        disk_size = ng.get("diskSize")
        if disk_size is not None:
            try:
                ds = int(disk_size)
                if not (20 <= ds <= 5000):
                    errors.append(f"{prefix}: diskSize={disk_size} must be between 20-5000.")
            except (ValueError, TypeError):
                errors.append(f"{prefix}: diskSize must be an integer.")

        num_nodes = ng.get("numNodes")
        if num_nodes is not None:
            try:
                nn = int(num_nodes)
                if not (0 <= nn <= 10):
                    errors.append(f"{prefix}: numNodes={num_nodes} must be between 0-10.")
            except (ValueError, TypeError):
                errors.append(f"{prefix}: numNodes must be an integer.")

    if errors:
        text = "\n".join(errors)
    else:
        text = "valid"

    return [types.TextContent(type="text", text=text)]


# ---------------------------------------------------------------------------
# ClusterHandler class
# ---------------------------------------------------------------------------

class ClusterHandler:

    def __init__(self, mcp, config: VksConfig, client: VksClient, allow_write: bool = False):
        self.mcp = mcp
        self.config = config
        self.client = client
        self.allow_write = allow_write

        # Read-only tools (always registered)
        self.mcp.tool(name="cluster_list")(self.cluster_list)
        self.mcp.tool(name="cluster_get")(self.cluster_get)
        self.mcp.tool(name="cluster_get_events")(self.cluster_get_events)
        self.mcp.tool(name="cluster_delete_dryrun")(self.cluster_delete_dryrun)
        self.mcp.tool(name="cluster_create_validate")(self.cluster_create_validate)

        # Write tools (only registered if allow_write is True)
        if self.allow_write:
            self.mcp.tool(name="cluster_create")(self.cluster_create)
            self.mcp.tool(name="cluster_update")(self.cluster_update)
            self.mcp.tool(name="cluster_delete")(self.cluster_delete)
            self.mcp.tool(name="cluster_auto_upgrade_config")(self.cluster_auto_upgrade_config)
            self.mcp.tool(name="cluster_auto_upgrade_delete")(self.cluster_auto_upgrade_delete)

    async def cluster_list(
        self,
        page: int | None = Field(None, description="Page number (starts at 0)"),
        pageSize: int | None = Field(None, description="Number of clusters per page (default 50)"),
        region: str | None = Field(None, description="Region override, e.g. 'HCM-3' or 'HAN'. Defaults to config region"),
    ) -> str:
        """Lists all VKS clusters in the configured region. Returns a markdown table with cluster name, ID, status, version, node count, and creation date. Supports pagination."""
        args = {}
        if page is not None:
            args["page"] = page
        if pageSize is not None:
            args["pageSize"] = pageSize
        if region is not None:
            args["region"] = region
        result = await _cluster_list(self.client, args)
        return result[0].text

    async def cluster_get(
        self,
        cluster_id: str = Field(..., description="VKS Cluster ID, e.g. 'k8s-2ff9b24c-a58c-497c-b526-79630b0d3c92'"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Gets full detail of a specific VKS cluster by ID. Returns a markdown key-value table with all cluster properties."""
        result = await _cluster_get(self.client, {"cluster_id": cluster_id, "region": region})
        return result[0].text

    async def cluster_create(
        self,
        body: dict = Field(..., description="CreateClusterComboDto body. Must include: name, releaseChannel, version, enablePrivateCluster, networkType, vpcId, subnetId, nodeGroups. Use cluster_create_validate first to check."),
        poc: bool = Field(False, description="Whether this is a Proof-of-Concept cluster"),
        autoRenewal: bool = Field(True, description="Enable auto-renewal for cluster subscription"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Creates a new VKS cluster. Requires --allow-write flag. Use cluster_create_validate first to check the body."""
        args = {"body": body, "poc": poc, "autoRenewal": autoRenewal}
        if region is not None:
            args["region"] = region
        result = await _cluster_create(self.client, args)
        return result[0].text

    async def cluster_update(
        self,
        cluster_id: str = Field(..., description="Cluster ID to update"),
        body: dict = Field(..., description="Fields to update (partial update supported)"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Updates an existing VKS cluster. Requires --allow-write flag."""
        result = await _cluster_update(
            self.client,
            {"cluster_id": cluster_id, "body": body, "region": region},
        )
        return result[0].text

    async def cluster_delete(
        self,
        cluster_id: str = Field(..., description="Cluster ID to delete. IRREVERSIBLE. Use cluster_delete_dryrun first."),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Deletes a VKS cluster. IRREVERSIBLE. Requires --allow-write flag. Use cluster_delete_dryrun first."""
        result = await _cluster_delete(
            self.client,
            {"cluster_id": cluster_id, "region": region},
        )
        return result[0].text

    async def cluster_get_kubeconfig(
        self,
        cluster_id: str = Field(..., description="Cluster ID to get kubeconfig for"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Gets the kubeconfig YAML for a VKS cluster. Returns raw YAML text."""
        result = await _cluster_get_kubeconfig(
            self.client,
            {"cluster_id": cluster_id, "region": region},
        )
        return result[0].text

    async def cluster_get_events(
        self,
        cluster_id: str = Field(..., description="Cluster ID"),
        page: int | None = Field(None, description="Page number (starts at 0)"),
        pageSize: int | None = Field(None, description="Items per page (default 20)"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Gets events for a VKS cluster. Returns a markdown table of events."""
        args = {"cluster_id": cluster_id}
        if page is not None:
            args["page"] = page
        if pageSize is not None:
            args["pageSize"] = pageSize
        if region is not None:
            args["region"] = region
        result = await _cluster_get_events(self.client, args)
        return result[0].text

    async def cluster_auto_upgrade_config(
        self,
        cluster_id: str = Field(..., description="Cluster ID"),
        weekdays: list[str] = Field(..., description="Days of week for auto-upgrade, e.g. ['Mon', 'Wed', 'Fri']"),
        time: str = Field(..., description="Time of day in HH:mm format, e.g. '03:00'"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Configures auto-upgrade schedule for a VKS cluster. Requires --allow-write flag."""
        args = {"cluster_id": cluster_id, "weekdays": weekdays, "time": time}
        if region is not None:
            args["region"] = region
        result = await _cluster_auto_upgrade_config(self.client, args)
        return result[0].text

    async def cluster_auto_upgrade_delete(
        self,
        cluster_id: str = Field(..., description="Cluster ID"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Deletes auto-upgrade configuration for a VKS cluster. Requires --allow-write flag."""
        result = await _cluster_auto_upgrade_delete(
            self.client,
            {"cluster_id": cluster_id, "region": region},
        )
        return result[0].text

    async def cluster_delete_dryrun(
        self,
        cluster_id: str = Field(..., description="Cluster ID to preview deletion for"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Preview what will be deleted when deleting a cluster. Shows cluster info and all node groups that will be removed."""
        result = await _cluster_delete_dryrun(
            self.client,
            {"cluster_id": cluster_id, "region": region},
        )
        return result[0].text

    def cluster_create_validate(
        self,
        body: dict = Field(..., description="CreateClusterComboDto body to validate. Checks name regex, required fields, disk size, node count, network type logic."),
    ) -> str:
        """Validates a CreateClusterComboDto body without actually creating a cluster. Returns 'valid' or a list of validation errors."""
        result = _cluster_create_validate({"body": body})
        return result[0].text
