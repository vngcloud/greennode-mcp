"""GreenNode MCP Server entry point."""
from __future__ import annotations

import argparse
import asyncio
import hmac
import os
import sys
from pathlib import Path
from typing import Annotated

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from mcp.server.fastmcp import FastMCP

from greennode.greenode_mcp_server.auth import TokenManager
from greennode.greenode_mcp_server.client import GreenodeClient
from greennode.greenode_mcp_server.config import load_config
from greennode.greenode_mcp_server.api_index import search as _search
from greennode.greenode_mcp_server.api_caller import call_api as _call_api
from greennode.greenode_mcp_server.k8s_handler import K8sHandler

CONFIG_PATH = Path.home() / ".greenode"

SERVER_INSTRUCTIONS = """
# GreenNode MCP Server

MCP Server for VNG Cloud — VKS, vServer, vLB, vStorage, vNetwork, DNS, CDN, vMonitor, vDB, and more.

## IMPORTANT: Operating mode

By default the server runs in **read-only** mode. Use `--allow-write` to enable write operations (POST, PUT, PATCH, DELETE).

## Workflow

1. Use `search_api` to discover which endpoint handles your task
2. Use `call_api` to execute the API call — auth token is injected automatically

## Available tools

### search_api
Discover VNG Cloud API endpoints by keyword.

### call_api
Execute any VNG Cloud REST API call with automatic IAM auth.

### Kubernetes Resource Management (requires kubeconfig from VKS API):
- list_k8s_resources: List K8s resources (Pods, Services, Deployments...)
- get_pod_logs: View pod logs
- get_k8s_events: View resource events
- list_api_versions: List available API versions
- manage_k8s_resource: CRUD single K8s resource (requires --allow-write for writes, --allow-sensitive-data-access for Secrets)
- apply_yaml: Apply YAML manifest (requires --allow-write)
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GreenNode MCP Server -- manage VNG Cloud services via MCP"
    )
    parser.add_argument(
        "--allow-write",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable write mode (POST, PUT, PATCH, DELETE operations)",
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
    parser.add_argument(
        "--refresh-specs",
        action="store_true",
        default=False,
        help="Bypass cached specs and force re-download from the spec registry",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=False,
        help="Do not contact the spec registry; use cached specs only",
    )
    return parser


def main() -> None:
    """Load config, register tools, and run the MCP server."""
    global mcp

    args = _build_parser().parse_args()
    api_key = args.api_key or os.environ.get("GRN_MCP_API_KEY")

    config = load_config(CONFIG_PATH)
    token_manager = TokenManager(config)
    client = GreenodeClient(config, token_manager)  # used by K8s handler only

    # Initialize spec registry (fetches/loads specs before tools are registered)
    from greennode.greenode_mcp_server.api_index import initialize_index
    initialize_index(refresh=args.refresh_specs, offline=args.offline)

    mcp = FastMCP("greenode-mcp-server", instructions=SERVER_INSTRUCTIONS)

    # --- search_api tool ---
    @mcp.tool(name="search_api")
    async def search_api_tool(
        query: Annotated[str, "Keywords to search for (e.g. 'create cluster', 'list load balancers')"],
        product: Annotated[
            str | None,
            "Filter by product: vks, vserver, vlb, vstorage, vnetwork, dns, cdn, vmonitor, vdb"
        ] = None,
    ) -> str:
        """Search VNG Cloud API endpoints by keyword. Use this to find which endpoint to call before using call_api."""
        results = _search(query, product)
        if not results:
            suffix = f" in product '{product}'" if product else ""
            return f"No API endpoints found matching '{query}'{suffix}."
        lines = [f"Found {len(results)} endpoint(s) matching '{query}':\n"]
        for entry in results:
            lines.append(entry.format())
            lines.append("")
        return "\n".join(lines)

    # --- call_api tool ---
    @mcp.tool(name="call_api")
    async def call_api_tool(
        method: Annotated[str, "HTTP method: GET, POST, PUT, PATCH, DELETE"],
        path: Annotated[str, "API path from search_api results (e.g. '/v1/clusters')"],
        product: Annotated[
            str | None,
            "Product slug (e.g. 'vks', 'vlb') — optional, helps resolve the correct base URL"
        ] = None,
        region: Annotated[str | None, "Region: HCM-3 or HAN (default: from config)"] = None,
        params: Annotated[dict | None, "Query parameters as a JSON object"] = None,
        body: Annotated[dict | None, "Request body as a JSON object (for POST/PUT/PATCH)"] = None,
    ) -> str:
        """Execute any VNG Cloud REST API call. IAM auth token is injected automatically.

Use search_api first to find the correct endpoint and required parameters.

**Pagination convention:** VNG Cloud APIs are 1-based — use `page=1` for the first page
(not `page=0`). Common param names: `page`, `size` (or `pageSize` in some products).
If the API returns `400 Page or size invalid`, try `page=1, size=10` or omit pagination
entirely to get backend defaults."""
        return await _call_api(
            method, path, product, region, params, body,
            config, token_manager, args.allow_write,
        )

    # --- K8s tools ---
    K8sHandler(
        mcp, config, client,
        allow_write=args.allow_write,
        allow_sensitive_data_access=args.allow_sensitive_data_access,
    )

    # --- Run ---
    if args.transport == "stdio":
        mcp.run()
    else:
        import uvicorn

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

        uv_config = uvicorn.Config(starlette_app, host=args.host, port=args.port, log_level="info")
        server = uvicorn.Server(uv_config)
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
