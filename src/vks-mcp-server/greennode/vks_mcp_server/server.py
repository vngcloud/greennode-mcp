"""GreenNode MCP Server entry point — follows EKS MCP Server handler pattern."""
from __future__ import annotations

import argparse
import asyncio
import hmac
import os
import sys
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Validate Authorization: Bearer <token> on every HTTP request."""

    def __init__(self, app, api_key: str) -> None:
        super().__init__(app)
        self._expected = f"Bearer {api_key}".encode()

    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("Authorization", "").encode()
        if not hmac.compare_digest(auth, self._expected):
            return Response(
                "Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)


def create_server() -> FastMCP:
    """Create and return a FastMCP server instance."""
    return FastMCP("vks-mcp-server", instructions=SERVER_INSTRUCTIONS)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
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
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode: stdio (default) or streamable-http",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for HTTP transport (default: 8000)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Bearer token to protect the HTTP endpoint (env: GRN_MCP_API_KEY)",
    )
    return parser


def main() -> None:
    """Load config, create handlers, and run the MCP server."""
    global mcp

    args = _build_parser().parse_args()
    api_key = args.api_key or os.environ.get("GRN_MCP_API_KEY")

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

    if args.transport == "stdio":
        mcp.run()
    else:
        # streamable-http mode
        import uvicorn  # optional dep; only required for streamable-http mode

        if not api_key:
            print(
                "Warning: --api-key not set. Server is unauthenticated. "
                "Only use in a trusted network.",
                file=sys.stderr,
            )

        mcp.settings.host = args.host
        mcp.settings.port = args.port

        loopback = {"127.0.0.1", "localhost", "::1"}
        if args.host not in loopback:
            from mcp.server.fastmcp.server import TransportSecuritySettings

            mcp.settings.transport_security = TransportSecuritySettings(
                enable_dns_rebinding_protection=False,
            )

        starlette_app = mcp.streamable_http_app()
        if api_key:
            starlette_app.add_middleware(BearerTokenMiddleware, api_key=api_key)

        uv_config = uvicorn.Config(
            starlette_app,
            host=args.host,
            port=args.port,
            log_level="info",
        )
        server = uvicorn.Server(uv_config)
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
