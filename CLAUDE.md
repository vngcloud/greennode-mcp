# CLAUDE.md — GreenNode MCP Servers

## Project overview

GreenNode MCP Servers provide AI assistants (Claude, Cursor, Gemini, etc.) with tools to manage GreenNode services via the Model Context Protocol.

- **Single server** — `greenode-mcp-server` covers all products via bundled OpenAPI specs
- **Namespace package** — `greennode.greenode_mcp_server`

### Available servers

| Server | Package | Tools |
|--------|---------|-------|
| GreenNode MCP Server | `greennode.greenode_mcp_server` | search_api, call_api, 6 K8s tools |

## Repository structure

```
greenode-mcp/
├── src/
│   └── greenode-mcp-server/
│       ├── pyproject.toml
│       ├── specs/                    # Bundled OpenAPI specs (*.json)
│       ├── greennode/
│       │   └── greenode_mcp_server/
│       └── tests/
├── scripts/
├── docs/
├── CLAUDE.md
└── pyproject.toml
```

## Code conventions

- All source code text must be in **English** — error messages, descriptions, comments, docstrings
- Async/await throughout — all handlers and client methods are async
- Use `from __future__ import annotations` in all files
- Follow existing handler pattern: class with `__init__` registering tools via `self.mcp.tool()`
- Package namespace: `greennode.greenode_mcp_server`
- Imports: `from greennode.greenode_mcp_server.config import ...` (not `greenode_mcp_server.config`)
- Mock paths in tests must also use `greennode.` prefix: `patch("greennode.greenode_mcp_server.module.Class")`

## VNG Cloud API quirks

- **IAM API uses camelCase**: `grantType`, `accessToken`, `expiresIn` (not snake_case OAuth2 standard)
- **VKS API pagination is 0-based**: page 0 = first page
- **API returns 202** for most successful operations (not 200)

## Adding a new tool (to existing server)

1. Choose the appropriate handler in `src/greenode-mcp-server/greennode/greenode_mcp_server/`
2. Define async method with docstring (used as tool description for AI)
3. Register in handler's `__init__`: `self.mcp.tool(name="tool_name")(self.method)`
4. Add `validate_id()` for any ID args used in URL construction
5. Check `self.allow_write` for mutating operations
6. Add tests in `src/greenode-mcp-server/tests/`

## Adding a new MCP server (new product)

The greenode-mcp-server now covers all products via bundled OpenAPI specs, so adding a new product typically means adding a new spec file to `src/greenode-mcp-server/specs/` rather than creating a separate server.

If a truly separate server is needed:

1. Create `src/<product>-mcp-server/` directory
2. Add per-product files: `pyproject.toml`, `uv.lock`, `LICENSE`, `NOTICE`, `CHANGELOG.md`, `.gitignore`, `.python-version`, `README.md`
3. Create `greennode/<product>_mcp_server/` for source code
4. Create `tests/` directory
5. Register entry point in `pyproject.toml`: `<product>-mcp-server = "greennode.<product>_mcp_server.server:main"`
6. Update root `README.md` available servers table

See `src/greenode-mcp-server/` as reference.

## Security rules

- **Input validation**: All resource IDs validated via `validators.validate_id()` before URL construction — prevents path traversal
- **Write guard**: Mutating operations must check `self.allow_write` flag
- **Sensitive data guard**: K8s Secret reads must check `self.allow_sensitive_data_access`
- **Credential env vars supported**: `GRN_ACCESS_KEY_ID`/`GRN_SECRET_ACCESS_KEY` override credentials file (highest priority)
- **Tokens in memory only**: Never written to disk or logged
- **Credentials not logged**: Error messages and debug logs never include tokens or secrets
- **Timeout**: All HTTP requests have 30s timeout
- **HTTP transport auth**: When `--transport streamable-http` is used, always set `--api-key` or `GRN_MCP_API_KEY` to protect the endpoint with bearer token auth
- **Unauthenticated HTTP warning**: If `--api-key` is not set in HTTP mode, server prints a warning to stderr and runs unauthenticated — only safe in trusted networks
- **Token comparison**: Bearer token uses `hmac.compare_digest` (constant-time) to prevent timing attacks
- **TLS**: Not handled by the server — use a reverse proxy for HTTPS in production

## Testing

```bash
cd src/greenode-mcp-server
uv sync --all-extras
uv run python -m pytest tests/ -v
```

- 65 tests for GreenNode MCP Server
- Uses `respx` for mocking async HTTP calls
- Uses `pytest-asyncio` for async test support

## Git workflow

- **Do not auto commit/push** — only change source code, user will ask for commit/push when ready
- **Main branch is protected** — cannot push directly, must use PR
- **Changelog**: Add fragment via `./scripts/new-change` for every change
- **Release**: `./scripts/bump-version minor` → `git push && git push --tags`

## Documentation update rule

**After ANY change to business logic, security, configuration, tools, or project structure:**

1. Review ALL docs below and update what's affected — do not skip this step
2. If unsure whether a doc needs updating, read it and check

**Docs to check:**

- `src/greenode-mcp-server/README.md` — Tool list, config, security, prerequisites
- `src/greenode-mcp-server/CHANGELOG.md` — Version history
- `README.md` (root) — Available servers, prerequisites, security
- `CLAUDE.md` — Conventions, rules, key files, security rules
- `docs/DEVELOPMENT.md` — Dev workflow, deployment, env vars
- `./scripts/new-change` — Add changelog fragment

**Examples:**
- Added/removed a tool → update README tool table + server.py SERVER_INSTRUCTIONS + CLAUDE.md tool count
- Changed auth/credentials flow → update README config section + root README prerequisites + CLAUDE.md security rules
- Changed project structure → update root README structure + CLAUDE.md repository structure
- Removed env var support → update all docs that mention env vars

Code without docs is not done.

## Key files (GreenNode MCP Server)

| File | Purpose |
|------|---------|
| `greennode/greenode_mcp_server/server.py` | FastMCP entry point, tool registration, CLI flags |
| `greennode/greenode_mcp_server/api_index.py` | Spec loader, in-memory index, keyword search |
| `greennode/greenode_mcp_server/api_caller.py` | call_api tool — write guard, auth injection, response formatting |
| `greennode/greenode_mcp_server/config.py` | Config loading, REGIONS dict |
| `greennode/greenode_mcp_server/auth.py` | TokenManager — async OAuth2 with auto-refresh |
| `greennode/greenode_mcp_server/client.py` | GreenodeClient — used by K8s handler for kubeconfig fetch |
| `greennode/greenode_mcp_server/k8s_handler.py` | 6 K8s tools |
| `greennode/greenode_mcp_server/k8s_apis.py` | K8s API client wrapper |
| `greennode/greenode_mcp_server/k8s_client_cache.py` | TTL cache for K8s clients |
| `greennode/greenode_mcp_server/models.py` | Pydantic models for K8s responses |

## Relationship with greenode-cli

Both projects share:
- Same config files (`~/.greenode/credentials`, `~/.greenode/config`)
- Same REGIONS dict (HCM-3, HAN endpoints)
- Same IAM auth flow (camelCase fields)
- Same env var names (`GRN_ACCESS_KEY_ID`, `GRN_SECRET_ACCESS_KEY`, `GRN_PROFILE`, `GRN_DEFAULT_REGION`, etc.)

Key differences:
- greenode-mcp is **async**, greenode-cli is **sync**
- greenode-mcp returns **markdown** (for AI readability), greenode-cli returns **JSON/table/text**
- greenode-mcp has **K8s resource management**, greenode-cli does not
