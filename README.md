# GreenNode MCP Servers

MCP (Model Context Protocol) Servers for GreenNode services. Provides AI assistants with tools to manage GreenNode infrastructure from natural language.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) lets AI assistants (Claude, Cursor, Gemini, etc.) interact with external tools and data sources. MCP servers expose tools that AI can call to perform actions on your behalf.

## Available MCP Servers

| Server | Description |
|--------|-------------|
| [GreenNode MCP Server](src/greenode-mcp-server/) | Manage GreenNode services via OpenAPI specs + K8s resource management |

## Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- GreenNode credentials — via environment variables or credentials file

### Credential setup

**Option A: Environment variables**

```bash
export GRN_ACCESS_KEY_ID=your-client-id
export GRN_SECRET_ACCESS_KEY=your-client-secret
export GRN_DEFAULT_REGION=HCM-3
export GRN_DEFAULT_PROJECT_ID=pro-xxxxxxxx   # required for many APIs that embed project in the URL
```

**Option B: GreenNode CLI (recommended)**

```bash
grn configure
```

The wizard auto-detects your `project_id` and writes:

- `~/.greenode/credentials` — `client_id`, `client_secret`
- `~/.greenode/config` — `region`, `project_id`, `output`

See [greenode-cli](https://github.com/vngcloud/greennode-cli).

Environment variables take priority over the files. All MCP servers in this repo read these same paths and env vars.

## Quick Start

Install and run with `uvx`:

```bash
uvx greenode-mcp-server
```

### Claude Desktop / Cursor configuration

```json
{
  "mcpServers": {
    "greennode": {
      "command": "uvx",
      "args": ["greenode-mcp-server", "--allow-write"]
    }
  }
}
```

## Repository Structure

```
greenode-mcp/
├── src/
│   └── greenode-mcp-server/            # GreenNode MCP Server
│       ├── README.md                    # Server-specific docs, tools, security
│       ├── pyproject.toml               # Package config + dependencies
│       ├── greennode/
│       │   └── greenode_mcp_server/     # Source code (incl. registry/ module)
│       └── tests/                       # Test suite
├── scripts/                             # Release scripts
├── docs/                                # Development guide
├── CLAUDE.md                            # AI assistant conventions
└── pyproject.toml                       # Root tool config
```

### Adding a new MCP server

Other product teams can add their MCP server:

1. Create `src/<product>-mcp-server/` directory
2. Add `pyproject.toml`, `LICENSE`, `NOTICE`, `CHANGELOG.md`, `.gitignore`, `.python-version`
3. Create `greennode/<product>_mcp_server/` for source code
4. Add `tests/` directory
5. Add `README.md` with tools, config, security docs
6. Update the [Available MCP Servers](#available-mcp-servers) table above

See [GreenNode MCP Server](src/greenode-mcp-server/) as reference.

## Security

All GreenNode MCP servers share these security principles:

- **Read-only by default** — Write operations require explicit `--allow-write` flag
- **Sensitive data protection** — Reading Kubernetes Secrets requires `--allow-sensitive-data-access`; other K8s reads (pods, deployments, logs, events) are allowed by default
- **Credential security** — `~/.greenode/credentials` stored with `0600` permissions
- **Input validation** — All resource IDs validated to prevent path traversal
- **Token handling** — In memory only, never written to disk or logged
- **Request safety** — 30s timeout, retry with exponential backoff

## Transport Mechanisms

The MCP protocol defines two standard transport mechanisms:

- **stdio** — communication over standard in/out. Default for all servers.
- **Streamable HTTP** — HTTP-based transport enabling remote hosting.

### Policy

| Transport | Status |
|-----------|--------|
| stdio | Supported (default) |
| SSE (Server Sent Events) | **Removed** — deprecated per [MCP spec 2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility) |
| Streamable HTTP | Supported in `greenode-mcp-server` via `--transport streamable-http` |

All servers in this repository default to **stdio** for local AI assistant use.
Streamable HTTP is available for self-hosted deployments. See each server's README for details.

## Getting Help

- [Open an issue](https://github.com/vngcloud/greenode-mcp/issues/new/choose) — Bug reports and feature requests
- Search [existing issues](https://github.com/vngcloud/greenode-mcp/issues) before opening a new one

## More Resources

- [GreenNode MCP Server](src/greenode-mcp-server/) — Tools, configuration, and security details
- [Development Guide](docs/DEVELOPMENT.md) — Contributing, CI/CD, release process
- [GreenNode CLI](https://github.com/vngcloud/greenode-cli) — CLI companion tool
- [MCP Protocol](https://modelcontextprotocol.io/) — Model Context Protocol specification
- [VNG Cloud Console](https://hcm-3.console.vngcloud.vn/)

## License

Apache License 2.0 — see [LICENSE](LICENSE).
