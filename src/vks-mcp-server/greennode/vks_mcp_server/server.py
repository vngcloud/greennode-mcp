"""GreenNode MCP Server entry point — follows EKS MCP Server handler pattern."""
from __future__ import annotations

import argparse
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from greennode.vks_mcp_server.auth import TokenManager
from greennode.vks_mcp_server.client import VksClient
from greennode.vks_mcp_server.config import load_config

from greennode.vks_mcp_server.auth_handler import AuthHandler
from greennode.vks_mcp_server.cluster_handler import ClusterHandler
from greennode.vks_mcp_server.k8s_handler import K8sHandler
from greennode.vks_mcp_server.nodegroup_handler import NodeGroupHandler
from greennode.vks_mcp_server.version_handler import VersionHandler

CONFIG_PATH = Path.home() / ".vks" / "config.json"

SERVER_INSTRUCTIONS = """
# GreenNode MCP Server

MCP Server for VNG Kubernetes Service (VKS).

## IMPORTANT: Operating mode

By default the server runs in **read-only** mode. Use the `--allow-write` flag to enable write operations (create, update, delete cluster/node group).

## Available tools

### Read-only (always available):
- get_access_token: Get the current access token
- cluster_list, cluster_get: View clusters
- cluster_get_kubeconfig: Get kubeconfig YAML
- cluster_get_events: View cluster events
- cluster_delete_dryrun: Preview information before deleting a cluster
- cluster_create_validate: Validate body before creating a cluster
- cluster_versions_list: List available Kubernetes versions
- nodegroup_list, nodegroup_get: View node groups
- nodegroup_list_nodes: List nodes in a node group
- nodegroup_delete_dryrun: Preview information before deleting a node group

### Write (requires --allow-write):
- cluster_create, cluster_update, cluster_delete: Create, update, delete cluster
- cluster_auto_upgrade_config, cluster_auto_upgrade_delete: Configure auto-upgrade
- cluster_auto_healing_config: Configure cluster auto-healing
- nodegroup_create, nodegroup_update, nodegroup_delete: Create, update, delete node group
- nodegroup_upgrade_version: Upgrade a node group's Kubernetes version

### Kubernetes Resource Management (requires kubeconfig from VKS API):
- list_k8s_resources: List K8s resources (Pods, Services, Deployments...)
- get_pod_logs: View pod logs
- get_k8s_events: View resource events
- list_api_versions: List API versions
- manage_k8s_resource: CRUD single K8s resource (requires --allow-write for write ops, --allow-sensitive-data-access for Secrets)
- apply_yaml: Apply YAML manifest file (requires --allow-write)
"""

mcp = None


def create_server() -> FastMCP:
    """Create and return a FastMCP server instance."""
    return FastMCP("vks-mcp-server", instructions=SERVER_INSTRUCTIONS)


def main() -> None:
    """Load config, create handlers, and run the MCP server."""
    global mcp

    parser = argparse.ArgumentParser(
        description="GreenNode MCP Server -- manage VNG Kubernetes Service via MCP"
    )
    parser.add_argument(
        "--allow-write",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable write mode (allow create, update, delete cluster/node group)",
    )
    parser.add_argument(
        "--allow-sensitive-data-access",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable access to sensitive data (required for reading Kubernetes Secrets)",
    )
    args = parser.parse_args()

    config = load_config(CONFIG_PATH)
    token_manager = TokenManager(config)
    client = VksClient(config, token_manager)

    mcp = create_server()

    AuthHandler(mcp, config, token_manager)
    ClusterHandler(mcp, config, client, allow_write=args.allow_write)
    NodeGroupHandler(mcp, config, client, allow_write=args.allow_write)
    VersionHandler(mcp, config, client)
    K8sHandler(
        mcp, config, client,
        allow_write=args.allow_write,
        allow_sensitive_data_access=args.allow_sensitive_data_access,
    )

    mcp.run()


if __name__ == "__main__":
    main()
