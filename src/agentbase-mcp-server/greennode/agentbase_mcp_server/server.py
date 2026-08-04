"""FastMCP entry point for the Agentbase MCP server (passthrough-only).

No service-account credentials: every upstream call forwards the caller's
bearer token. stdio reads the token from an env var at startup; HTTP gates
each request on the Authorization header (see middleware.py).
"""

from __future__ import annotations

import argparse
import os
import sys
from greennode.agentbase_mcp_server.auth import PassthroughTokenManager
from greennode.agentbase_mcp_server.client import AgentbaseClient
from greennode.agentbase_mcp_server.config import load_config
from greennode.agentbase_mcp_server.discovery_cache import DiscoveryCache
from greennode.agentbase_mcp_server.middleware import PassthroughIdentityMiddleware
from greennode.agentbase_mcp_server.policy_handler import PolicyHandler
from greennode.mcp_core.http import user_token_var
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


SERVER_INSTRUCTIONS = """\
GreenNode Agentbase MCP Server (policy service — pilot).

Runs **passthrough-only**: the server holds no service-account credentials.
Every upstream call forwards the caller's IAM bearer token from the
Authorization header (HTTP) or the GREENNODE_MCP_TOKEN env var (stdio).

By default the server runs in **read-only** mode. Use `--allow-write` to
enable create/update/delete. `get_authorization_decision` is always available
(read-only evaluation, POST-but-read).
"""


def create_server(allow_write: bool = False) -> FastMCP:
    """Create and return a FastMCP server instance (handlers wired in main)."""
    server = FastMCP("agentbase-mcp-server", instructions=SERVER_INSTRUCTIONS)

    @server.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> Response:
        """Liveness/readiness probe (no authentication required)."""
        return JSONResponse({"status": "ok"})

    return server


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="GreenNode MCP Server -- manage Agentbase (policy) via MCP"
    )
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help="Enable create/update/delete operations (default: read-only)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode: stdio (default) or streamable-http",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host for HTTP transport")
    parser.add_argument("--port", type=int, default=8080, help="Bind port for HTTP transport")
    return parser


def _stdio_token_or_exit() -> str:
    """Read the caller token for stdio from env; exit non-zero if missing."""
    token_env = os.environ.get("TOKEN_ENV", "GREENNODE_MCP_TOKEN")
    token = os.environ.get(token_env, "").strip()
    if not token:
        sys.stderr.write(
            f"Passthrough-only server: env var {token_env} is unset or empty on "
            "stdio transport. Set it to the caller's IAM bearer token.\n"
        )
        raise SystemExit(1)
    return token


def main() -> None:
    """Run the MCP server with passthrough auth."""
    args = _build_parser().parse_args()
    config = load_config()
    token_manager = PassthroughTokenManager()
    client = AgentbaseClient(config, token_manager)

    mcp = create_server(allow_write=args.allow_write)
    cache = DiscoveryCache()
    PolicyHandler(mcp, config, client, cache, allow_write=args.allow_write)

    if args.transport == "streamable-http":
        import uvicorn  # optional dep; only required for streamable-http

        mcp.settings.host = args.host
        mcp.settings.port = args.port
        loopback = {"127.0.0.1", "localhost", "::1"}
        if args.host not in loopback:
            from mcp.server.fastmcp.server import TransportSecuritySettings

            mcp.settings.transport_security = TransportSecuritySettings(
                enable_dns_rebinding_protection=False,
            )
        starlette_app = mcp.streamable_http_app()
        starlette_app.add_middleware(PassthroughIdentityMiddleware)
        uvicorn.run(starlette_app, host=args.host, port=args.port)
    else:
        # stdio: one caller token for the process lifetime.
        user_token_var.set(_stdio_token_or_exit())
        mcp.run()


if __name__ == "__main__":
    main()
