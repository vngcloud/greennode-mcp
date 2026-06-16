# GreenNode MCP Server (VKS)

An MCP (Model Context Protocol) server that gives AI assistants (Claude, Cursor,
Gemini, etc.) tools to manage **VKS — VNG Kubernetes Service** clusters and the
Kubernetes resources inside them.

- **27 tools** across 5 handlers: Auth, Cluster, NodeGroup, Version, K8s
- Fully **async** (httpx) on the **FastMCP** framework
- Read-only by default; write and sensitive-data access are opt-in via flags

## Installation

Requires Python ≥ 3.11. Using [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

## Configuration

Credentials and region are read from `~/.greenode/credentials` and
`~/.greenode/config` (INI format, shared with greenode-cli).

Environment variables override the config files (highest priority):

| Variable | Purpose |
|----------|---------|
| `GRN_CLIENT_ID` | Override client_id |
| `GRN_CLIENT_SECRET` | Override client_secret |
| `GRN_PROFILE` | Select profile (default: `default`) |
| `GRN_DEFAULT_REGION` | Override region |

## Running

```bash
# Read-only mode (default)
uv run vks-mcp-server

# Enable create/update/delete operations
uv run vks-mcp-server --allow-write

# Enable reading Kubernetes Secrets / logs / events
uv run vks-mcp-server --allow-sensitive-data-access
```

The server speaks MCP over stdio, so point your MCP client (Claude Desktop,
Cursor, …) at the command above.

## Tools

- **Cluster** — list/get/create/update/delete, kubeconfig, events, auto-upgrade,
  delete dry-run, create validation
- **NodeGroup** — list/get/create/update/delete, list nodes, delete dry-run
- **Version** — list cluster versions, list node-group images
- **Kubernetes** — list resources, manage a single resource (CRUD), apply YAML,
  pod logs, resource events, list API versions
- **Auth** — get the current access token

## Development

```bash
uv run python -m pytest tests/ -v
```

Tests use `respx` for async HTTP mocking and `pytest-asyncio`. See `CLAUDE.md`
for conventions on adding new tools.

## License

Apache-2.0. See [LICENSE](LICENSE).
