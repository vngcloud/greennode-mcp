# GreenNode MCP Servers

MCP (Model Context Protocol) Servers for GreenNode services. Provides AI assistants with tools to manage GreenNode infrastructure from natural language.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) lets AI assistants (Claude, Cursor, Gemini, etc.) interact with external tools and data sources. MCP servers expose tools that AI can call to perform actions on your behalf.

## Available MCP Servers

| Server | Description |
|--------|-------------|
| [VKS MCP Server](src/vks-mcp-server/) | Manage VKS (VNG Kubernetes Service) clusters, node groups, and K8s resources |

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
```

**Option B: Credentials file (via GreenNode CLI)**

```bash
pip install grncli
grn configure
```

This creates `~/.greenode/credentials` which all MCP servers read automatically. Environment variables take priority over the credentials file.

> **Note:** All MCP servers require credentials configured via one of these methods.

## Repository Structure

```
greennode-mcp/
├── src/
│   └── vks-mcp-server/              # VKS MCP Server
│       ├── README.md                 # VKS-specific docs, tools, security
│       ├── pyproject.toml            # Package config + dependencies
│       ├── uv.lock                   # Lock file
│       ├── LICENSE                   # Apache 2.0
│       ├── NOTICE                    # Copyright notice
│       ├── CHANGELOG.md             # Version history
│       ├── .gitignore
│       ├── .python-version           # Python 3.10
│       ├── greennode/
│       │   └── vks_mcp_server/       # Source code
│       │       ├── server.py         # Entry point
│       │       ├── cluster_handler.py
│       │       ├── nodegroup_handler.py
│       │       ├── k8s_handler.py
│       │       └── ...
│       └── tests/                    # Test suite
├── scripts/                          # Release scripts
├── docs/                             # Development guide
├── CLAUDE.md                         # AI assistant conventions
└── pyproject.toml                    # Root tool config
```

### Adding a new MCP server

Other product teams can add their MCP server:

1. Create `src/<product>-mcp-server/` directory
2. Add `pyproject.toml`, `LICENSE`, `NOTICE`, `CHANGELOG.md`, `.gitignore`, `.python-version`
3. Create `greennode/<product>_mcp_server/` for source code
4. Add `tests/` directory
5. Add `README.md` with tools, config, security docs
6. Update the [Available MCP Servers](#available-mcp-servers) table above

See [VKS MCP Server](src/vks-mcp-server/) as reference.

## Security

All GreenNode MCP servers share these security principles:

- **Read-only by default** — Write operations require explicit `--allow-write` flag
- **Sensitive data protection** — Kubernetes Secrets require `--allow-sensitive-data-access`
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
| Streamable HTTP | Supported in `vks-mcp-server` via `--transport streamable-http` |

All servers in this repository default to **stdio** for local AI assistant use.
Streamable HTTP is available for self-hosted deployments. See each server's README for details.

## Getting Help

- [Open an issue](https://github.com/vngcloud/greennode-mcp/issues/new/choose) — Bug reports and feature requests
- Search [existing issues](https://github.com/vngcloud/greennode-mcp/issues) before opening a new one

## More Resources

- [VKS MCP Server](src/vks-mcp-server/) — VKS tools, configuration, and security details
- [Development Guide](docs/DEVELOPMENT.md) — Contributing, CI/CD, release process
- [GreenNode CLI](https://github.com/vngcloud/greennode-cli) — CLI companion tool
- [MCP Protocol](https://modelcontextprotocol.io/) — Model Context Protocol specification
- [VNG Cloud Console](https://hcm-3.console.vngcloud.vn/)

## License

Apache License 2.0 — see [LICENSE](LICENSE).
