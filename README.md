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
- [GreenNode CLI](https://github.com/vngcloud/greennode-cli) (`grncli`) — **required** for credential setup

```bash
pip install grncli
grn configure
```

> **Note:** All MCP servers read credentials from `~/.greenode/credentials`, which is created by `grn configure`. The servers cannot run without this file.

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
