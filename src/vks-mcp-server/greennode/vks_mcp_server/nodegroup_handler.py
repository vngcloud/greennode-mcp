"""Node group management handler for GreenNode MCP Server."""

from __future__ import annotations

import json
from greennode.vks_mcp_server.client import VksClient
from greennode.vks_mcp_server.config import VksConfig
from greennode.vks_mcp_server.models import format_nodegroup_detail, format_nodegroup_table
from greennode.vks_mcp_server.validators import validate_id
from pydantic import Field


# ---------------------------------------------------------------------------
# Internal implementation functions
# ---------------------------------------------------------------------------


async def _nodegroup_list(
    config: VksConfig,
    client: VksClient,
    cluster_id: str,
    region: str | None = None,
) -> str:
    """Fetch node groups and cluster name, return formatted table."""
    validate_id(cluster_id, "cluster_id")
    items = await client.get(f"/v1/clusters/{cluster_id}/node-groups", region=region)
    if isinstance(items, dict):
        items = items.get("items", items.get("nodeGroups", [items]))

    # Try to get cluster name
    cluster_name = cluster_id
    try:
        cluster = await client.get(f"/v1/clusters/{cluster_id}", region=region)
        cluster_name = cluster.get("name", cluster_id)
    except Exception:
        pass

    return format_nodegroup_table(items, cluster_name)


async def _nodegroup_delete_dryrun(
    config: VksConfig,
    client: VksClient,
    cluster_id: str,
    nodegroup_id: str,
    region: str | None = None,
) -> str:
    """Preview node group deletion."""
    validate_id(cluster_id, "cluster_id")
    validate_id(nodegroup_id, "nodegroup_id")
    ng = await client.get(
        f"/v1/clusters/{cluster_id}/node-groups/{nodegroup_id}",
        region=region,
    )

    name = ng.get("name", nodegroup_id)
    ngid = ng.get("uid", "") or ng.get("id", nodegroup_id)
    status = ng.get("status", "")
    node_count = ng.get("nodeCount", ng.get("numNodes", ""))

    warning = (
        f"WARNING: YOU ARE ABOUT TO DELETE NODE GROUP:\n\n"
        f"| Property | Value |\n"
        f"|---|---|\n"
        f"| Name | {name} |\n"
        f"| ID | {ngid} |\n"
        f"| Cluster ID | {cluster_id} |\n"
        f"| Status | {status} |\n"
        f"| Node count | {node_count} |\n\n"
        f"This action is IRREVERSIBLE. Call `nodegroup_delete` to confirm deletion."
    )

    return warning


# ---------------------------------------------------------------------------
# NodeGroupHandler class
# ---------------------------------------------------------------------------


class NodeGroupHandler:
    """Register and serve VKS node-group-management MCP tools."""

    def __init__(self, mcp, config: VksConfig, client: VksClient, allow_write: bool = False):
        self.mcp = mcp
        self.config = config
        self.client = client
        self.allow_write = allow_write

        # Read-only tools
        self.mcp.tool(name="nodegroup_list")(self.nodegroup_list)
        self.mcp.tool(name="nodegroup_get")(self.nodegroup_get)
        self.mcp.tool(name="nodegroup_list_nodes")(self.nodegroup_list_nodes)
        self.mcp.tool(name="nodegroup_delete_dryrun")(self.nodegroup_delete_dryrun)

        # Write tools
        if self.allow_write:
            self.mcp.tool(name="nodegroup_create")(self.nodegroup_create)
            self.mcp.tool(name="nodegroup_update")(self.nodegroup_update)
            self.mcp.tool(name="nodegroup_delete")(self.nodegroup_delete)
            self.mcp.tool(name="nodegroup_upgrade_version")(self.nodegroup_upgrade_version)

    async def nodegroup_list(
        self,
        cluster_id: str = Field(..., description="VKS Cluster ID"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Lists all node groups in a VKS cluster. Returns a markdown table."""
        return await _nodegroup_list(
            self.config,
            self.client,
            cluster_id=cluster_id,
            region=region,
        )

    async def nodegroup_get(
        self,
        cluster_id: str = Field(..., description="VKS Cluster ID"),
        nodegroup_id: str = Field(
            ..., description="Node Group ID, e.g. 'ng-f5674ebc-30be-47e2-b4ef-5d4474deae58'"
        ),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Gets full detail of a specific node group. Returns a markdown key-value table."""
        validate_id(cluster_id, "cluster_id")
        validate_id(nodegroup_id, "nodegroup_id")
        ng = await self.client.get(
            f"/v1/clusters/{cluster_id}/node-groups/{nodegroup_id}",
            region=region,
        )
        return format_nodegroup_detail(ng)

    async def nodegroup_create(
        self,
        cluster_id: str = Field(..., description="VKS Cluster ID to add the node group to"),
        body: dict = Field(
            ...,
            description=(
                "CreateNodeGroupDto body (JSON object). Required fields: name, "
                "numNodes (0-10), flavorId, diskSize (20-5000), diskType, "
                "enablePrivateNodes, securityGroups, sshKeyId, upgradeConfig "
                "(optional: os = ubuntu|linux)."
            ),
        ),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Create a new node group in a VKS cluster.

        ## Requirements
        - Server must run with --allow-write
        """
        validate_id(cluster_id, "cluster_id")
        result = await self.client.post(
            f"/v1/clusters/{cluster_id}/node-groups",
            region=region,
            json=body,
        )
        return f"Node group created successfully:\n```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"

    async def nodegroup_update(
        self,
        cluster_id: str = Field(..., description="VKS Cluster ID"),
        nodegroup_id: str = Field(..., description="Node Group ID to update"),
        body: dict = Field(
            ...,
            description=(
                "Update body (JSON object). No fields are required. Optional: "
                "numNodes (0-10), securityGroups, labels, taints, autoScaleConfig, "
                "upgradeConfig."
            ),
        ),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Updates a node group. Requires --allow-write flag."""
        validate_id(cluster_id, "cluster_id")
        validate_id(nodegroup_id, "nodegroup_id")
        result = await self.client.put(
            f"/v1/clusters/{cluster_id}/node-groups/{nodegroup_id}",
            region=region,
            json=body,
        )
        return f"Node group updated successfully:\n```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"

    async def nodegroup_delete(
        self,
        cluster_id: str = Field(..., description="VKS Cluster ID"),
        nodegroup_id: str = Field(..., description="Node Group ID to delete. IRREVERSIBLE."),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Deletes a node group. IRREVERSIBLE. Requires --allow-write flag. Use nodegroup_delete_dryrun first."""
        validate_id(cluster_id, "cluster_id")
        validate_id(nodegroup_id, "nodegroup_id")
        await self.client.delete(
            f"/v1/clusters/{cluster_id}/node-groups/{nodegroup_id}",
            region=region,
        )
        return (
            f"Delete request for node group `{nodegroup_id}`"
            f" in cluster `{cluster_id}` submitted successfully."
        )

    async def nodegroup_upgrade_version(
        self,
        cluster_id: str = Field(..., description="VKS Cluster ID"),
        nodegroup_id: str = Field(..., description="Node Group ID to upgrade"),
        kubernetes_version: str = Field(
            ...,
            description="Target Kubernetes version. Use cluster_versions_list to see valid versions.",
        ),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Upgrade a node group's Kubernetes version.

        ## Requirements
        - Server must run with --allow-write
        """
        validate_id(cluster_id, "cluster_id")
        validate_id(nodegroup_id, "nodegroup_id")
        result = await self.client.post(
            f"/v1/clusters/{cluster_id}/node-groups/{nodegroup_id}/upgrade-version",
            region=region,
            json={"kubernetesVersion": kubernetes_version},
        )
        return (
            f"Node group `{nodegroup_id}` upgrade to Kubernetes version "
            f"`{kubernetes_version}` requested successfully.\n```json\n"
            f"{json.dumps(result, indent=2, ensure_ascii=False)}\n```"
        )

    async def nodegroup_list_nodes(
        self,
        cluster_id: str = Field(..., description="VKS Cluster ID"),
        nodegroup_id: str = Field(..., description="Node Group ID"),
        page: int | None = Field(None, ge=0, description="Page number (starts at 0)"),
        pageSize: int | None = Field(None, ge=1, description="Items per page (default 50)"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Lists nodes in a node group. Returns a markdown table."""
        validate_id(cluster_id, "cluster_id")
        validate_id(nodegroup_id, "nodegroup_id")
        params = {}
        if page is not None:
            params["page"] = page
        if pageSize is not None:
            params["pageSize"] = pageSize

        result = await self.client.get(
            f"/v1/clusters/{cluster_id}/node-groups/{nodegroup_id}/nodes",
            region=region,
            params=params or None,
        )

        if isinstance(result, dict):
            nodes = result.get("items", result.get("nodes", []))
        else:
            nodes = result if isinstance(result, list) else []

        if not nodes:
            return "No nodes found in this node group."

        header = "| # | Name | ID | Status | IP | Created |"
        separator = "|---|---|---|---|---|---|"
        rows = []
        for i, node in enumerate(nodes, start=1):
            name = node.get("name", "")
            nid = node.get("uid", "") or node.get("id", "")
            status = node.get("status", "")
            ip = node.get("ipAddress", "") or node.get("ip", "")
            created = str(node.get("createdAt", ""))[:10]
            rows.append(f"| {i} | {name} | {nid} | {status} | {ip} | {created} |")

        text = "\n".join([header, separator] + rows)
        return f"Nodes list (node group: {nodegroup_id}):\n\n" + text

    async def nodegroup_delete_dryrun(
        self,
        cluster_id: str = Field(..., description="VKS Cluster ID"),
        nodegroup_id: str = Field(..., description="Node Group ID to preview deletion for"),
        region: str | None = Field(None, description="Region override"),
    ) -> str:
        """Preview what will be deleted when deleting a node group."""
        return await _nodegroup_delete_dryrun(
            self.config,
            self.client,
            cluster_id=cluster_id,
            nodegroup_id=nodegroup_id,
            region=region,
        )
