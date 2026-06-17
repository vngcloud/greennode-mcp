# CLAUDE.md — GreenNode MCP Server

## Project overview

GreenNode MCP Server provides AI assistants (Claude, Cursor, Gemini, etc.) with tools to manage VKS (VNG Kubernetes Service) clusters and Kubernetes resources via the Model Context Protocol.

- **27 tools** across 5 handlers: Auth, Cluster, NodeGroup, Version, K8s
- **Async architecture** — fully async/await with httpx.AsyncClient
- **FastMCP framework** — uses `mcp` library for tool registration

## Repository layout

Monorepo organized as a **uv workspace** (root `pyproject.toml`, `members = ["src/*"]`), mirroring the AWS Labs MCP layout. Each product is an independent project under `src/` sharing the `greennode` namespace.

- Product project: `src/vks-mcp-server/` (own `pyproject.toml`, `tests/`, `README.md`, `Dockerfile`, …)
- Import package: `greennode.vks_mcp_server` (source under `src/vks-mcp-server/greennode/vks_mcp_server/`)
- CLI entry point: `vks-mcp-server` → `greennode.vks_mcp_server.server:main`
- Future products: add as `src/<name>-mcp-server/` siblings under the same `greennode` namespace

## Code conventions

- All source code text must be in **English** — error messages, descriptions, comments, docstrings
- Async/await throughout — all handlers and client methods are async
- Use `from __future__ import annotations` in all files
- Follow existing handler pattern: class with `__init__` registering tools via `self.mcp.tool()`

## VNG Cloud API quirks

- **IAM API uses camelCase**: `grantType`, `accessToken`, `expiresIn` (not snake_case OAuth2 standard)
- **VKS API pagination is 0-based**: page 0 = first page
- **API returns 202** for most successful operations (not 200)

## Configuration

Reads from `~/.greenode/credentials` and `~/.greenode/config` (INI format, shared with greenode-cli).

**Environment variable overrides** (highest priority):

| Variable | Purpose |
|----------|---------|
| `GRN_CLIENT_ID` | Override client_id |
| `GRN_CLIENT_SECRET` | Override client_secret |
| `GRN_PROFILE` | Select profile (default: "default") |
| `GRN_DEFAULT_REGION` | Override region |

## Server flags

```bash
# Read-only mode (default)
uv run vks-mcp-server

# Enable create/update/delete operations
uv run vks-mcp-server --allow-write

# Enable reading Kubernetes Secrets
uv run vks-mcp-server --allow-sensitive-data-access
```

## Adding a new tool

1. Choose the appropriate handler or create a new one in `src/vks-mcp-server/greennode/vks_mcp_server/`
2. Define async method with docstring (used as tool description)
3. Register in handler's `__init__`: `self.mcp.tool(name="tool_name")(self.method)`
4. Add `validate_id()` for any ID args used in URL construction
5. Check `self.allow_write` for mutating operations
6. Register handler in `server.py` if new handler class
7. Add tests in `tests/`
8. Use `Literal[...]` for parameters with a fixed value set, and `Field(ge=, le=)` for numeric bounds, so the schema is self-documenting
9. For `body: dict` params, list required fields, valid values, and conditional logic in the Field description
10. Write structured docstrings (`## Requirements`, `## Workflow`) for create/update/delete tools

Example:
```python
async def my_tool(self, cluster_id: str) -> str:
    """Tool description shown to AI assistant."""
    validate_id(cluster_id, "cluster-id")
    client = self.client
    result = await client.get(f"/v1/clusters/{cluster_id}/my-endpoint")
    return format_result(result)
```

## Security rules

- **Input validation**: All cluster-id and nodegroup-id must be validated via `validators.validate_id()` before URL construction — prevents path traversal
- **Write guard**: Mutating operations must check `self.allow_write` flag
- **Sensitive data guard**: K8s Secret reads must check `self.allow_sensitive_data_access`
- **Tokens in memory only**: Never written to disk or logged
- **Credentials not logged**: Error messages and debug logs never include tokens or secrets
- **Timeout**: All HTTP requests have 30s timeout to prevent hanging

## HTTP Client

`VksClient` in `client.py`:
- Async httpx client with Bearer token auth
- **Retry logic**: Max 3 retries with exponential backoff (1s → 2s → 4s) for 5xx and timeout errors
- **401 handling**: Auto-refresh token and retry once
- **Timeout**: 30s on all requests

## Testing

```bash
cd src/vks-mcp-server && uv run pytest tests/ -v
```

- 51 tests covering all handlers (incl. tool-schema introspection)
- Uses `respx` for mocking async HTTP calls
- Uses `pytest-asyncio` for async test support

## Key files

| File | Purpose |
|------|---------|
| `server.py` | FastMCP entry point, handler registration, CLI flags |
| `config.py` | Config loading from `~/.greenode/`, env var overrides, REGIONS dict |
| `auth.py` | TokenManager — async OAuth2 Client Credentials with auto-refresh |
| `client.py` | VksClient — async HTTP with retry + token refresh |
| `validators.py` | ID format validation |
| `cluster_handler.py` | 11 cluster tools (CRUD + kubeconfig + events + auto-upgrade + validation) |
| `nodegroup_handler.py` | 7 nodegroup tools (CRUD + nodes + dry-run) |
| `k8s_handler.py` | 7 K8s tools (list/manage resources + logs + events + apply YAML + generate app manifest) |
| `k8s_apis.py` | K8s API client wrapper using kubernetes library |
| `k8s_client_cache.py` | TTL cache for K8s clients (840s) |
| `version_handler.py` | 1 tool (cluster versions) |
| `models.py` | Pydantic models + markdown formatters for responses |

## Documentation update rule

After completing any feature or bugfix, update ALL related documentation:

1. **README.md** — Update tool list, usage examples if changed
2. **CLAUDE.md** — Update tool count, key files if new files added
3. **Changelog** — Add entry describing the change

Code without docs is not done.

## Relationship with greenode-cli

Both projects share:
- Same config files (`~/.greenode/credentials`, `~/.greenode/config`)
- Same REGIONS dict (HCM-3, HAN endpoints)
- Same IAM auth flow (camelCase fields)
- Same env var names (`GRN_CLIENT_ID`, etc.)

Key differences:
- greenode-mcp is **async**, greenode-cli is **sync**
- greenode-mcp returns **markdown** (for AI readability), greenode-cli returns **JSON/table/text**
- greenode-mcp has **K8s resource management**, greenode-cli does not
