# CLAUDE.md — GreenNode MCP Servers

## Project overview

GreenNode MCP Servers provide AI assistants (Claude, Cursor, Gemini, etc.) with tools to manage GreenNode services via the Model Context Protocol.

- **Single server** — `greenode-mcp-server` covers all VNG Cloud products via a spec registry (`docs.api.vngcloud.vn`, fetched at startup, cached at `~/.greenode/mcp-specs/`)
- **Namespace package** — `greennode.greenode_mcp_server`

### Available servers

| Server | Package | Tools |
|--------|---------|-------|
| GreenNode MCP Server | `greennode.greenode_mcp_server` | `search_api`, `call_api`, 6 K8s tools (`list_k8s_resources`, `get_pod_logs`, `get_k8s_events`, `list_api_versions`, `manage_k8s_resource`, `apply_yaml`) |

## Repository structure

```
greenode-mcp/
├── src/
│   └── greenode-mcp-server/
│       ├── pyproject.toml
│       ├── greennode/
│       │   └── greenode_mcp_server/
│       │       ├── registry/        # Spec registry (provider + cache + loader)
│       │       ├── _build_info.py   # Build-time baked DEFAULT_DOCS_PORTAL_URL
│       │       └── ...
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
- **Pagination is 1-based across VNG Cloud APIs**: page 1 = first page (standard convention for all products)
- **API returns 202** for most successful operations (not 200)
- **List response wrapper keys vary**: `items`, `listData`, `data`, `results`, `records` — the formatter in `api_caller.py` recognises all of them
- **`{projectId}` / `{project_id}` path placeholders** are auto-substituted by `call_api` from `config.default_project_id` (set by `grn configure` or `GRN_DEFAULT_PROJECT_ID` env var)
- **K8s `api_version`** is optional for common kinds (Pod, Deployment, PVC, ...) via `COMMON_API_VERSIONS` in `k8s_handler.py`; custom resources still need it explicit
- **VKS kubeconfig endpoint** returns `{kubeConfig: "<yaml>", status: "ACTIVE"|"CREATING"|...}` — not raw YAML. `k8s_client_cache.py` extracts the `kubeConfig` field and checks `status`

## Adding a new tool (to existing server)

1. Choose the appropriate handler in `src/greenode-mcp-server/greennode/greenode_mcp_server/`
2. Define async method with docstring (used as tool description for AI)
3. Register in handler's `__init__`: `self.mcp.tool(name="tool_name")(self.method)`
4. Add `validate_id()` for any ID args used in URL construction
5. Check `self.allow_write` for mutating operations
6. Add tests in `src/greenode-mcp-server/tests/`

## Adding a new MCP server (new product)

The greenode-mcp-server covers all products via the spec registry (`docs.api.vngcloud.vn`). Adding a new product = VNG Cloud team publishes the product's OpenAPI page on the docs portal. The server picks it up on next restart — no code change, no release needed.

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
- **Sensitive data guard**: Only K8s Secret reads check `self.allow_sensitive_data_access`. Pod logs and K8s events are NOT guarded — they're routine debug reads
- **Credential env vars supported**: `GRN_ACCESS_KEY_ID`/`GRN_SECRET_ACCESS_KEY` override credentials file; `GRN_DEFAULT_PROJECT_ID` overrides config file `project_id` (highest priority)
- **Response size cap**: `call_api` rejects responses > 800 KB with an actionable error — prevents context blow-up
- **Row cap**: list responses truncate at 100 rows by default (with a footer telling the caller to paginate)
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

- ~175 tests for GreenNode MCP Server
- Uses `respx` for mocking async HTTP calls
- Uses `pytest-asyncio` for async test support
- MCP protocol smoke test: `python3 scripts/mcp_protocol_smoke.py` (runs the server via stdio, walks initialize → tools/list → tools/call)

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
| `greennode/greenode_mcp_server/server.py` | FastMCP entry point, tool registration, CLI flags (`--refresh-specs`, `--offline`, ...) |
| `greennode/greenode_mcp_server/api_index.py` | In-memory endpoint index, keyword search; delegates loading to `registry/` |
| `greennode/greenode_mcp_server/api_caller.py` | call_api tool — write guard, auth injection, response formatting |
| `greennode/greenode_mcp_server/_build_info.py` | Build-time baked `DEFAULT_DOCS_PORTAL_URL` (CI overwrites at release) |
| `greennode/greenode_mcp_server/registry/provider.py` | `SpecProvider` Protocol, `ProductRef`, error types |
| `greennode/greenode_mcp_server/registry/factory.py` | Selects active provider (swap here to migrate sources) |
| `greennode/greenode_mcp_server/registry/redocly_portal.py` | Default provider — scrapes docs portal inline OpenAPI JSON |
| `greennode/greenode_mcp_server/registry/local_dir.py` | Dev/test provider — reads specs from `GRN_MCP_SPEC_DIR` |
| `greennode/greenode_mcp_server/registry/cache.py` | On-disk spec cache at `~/.greenode/mcp-specs/` with TTL + ETag |
| `greennode/greenode_mcp_server/registry/loader.py` | Orchestrator — ties provider + cache + CLI flags together |
| `greennode/greenode_mcp_server/config.py` | `GreenodeConfig` loader — reads `~/.greenode/credentials` + `~/.greenode/config` (incl. `project_id`), env-var overrides, REGIONS dict |
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
- Same env var names (`GRN_ACCESS_KEY_ID`, `GRN_SECRET_ACCESS_KEY`, `GRN_PROFILE`, `GRN_DEFAULT_REGION`, `GRN_DEFAULT_PROJECT_ID`)
- Same profile section convention (`[default]` vs `[profile <name>]` in the config file, AWS-style)
- `grn configure` auto-detects `project_id` and writes it to `~/.greenode/config` — MCP reads that value without a separate API call

Key differences:
- greenode-mcp is **async**, greenode-cli is **sync**
- greenode-mcp returns **markdown** (for AI readability), greenode-cli returns **JSON/table/text**
- greenode-mcp has **K8s resource management**, greenode-cli does not
