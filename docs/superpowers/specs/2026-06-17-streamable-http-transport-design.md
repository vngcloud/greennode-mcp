# Design: Restore Streamable HTTP transport (for remote MCP behind MCP Gateway)

Date: 2026-06-17

## Context

To use greennode-mcp as a **remote** MCP server behind the GreenNode **MCP
Gateway** (Agent Base MCP Governance), the server must expose an HTTP endpoint —
the Gateway proxies agent calls to a registered "MCP endpoint URL" (HTTPS) and
handles inbound auth (JWT/IAM) + Policy Group. greennode-mcp currently runs
**stdio only** (`mcp.run()`); it has no HTTP endpoint.

This transport was previously implemented on branch
`feat/mcp-streamable-http-transport` (commit `4ea0522`) but was **regressed out
of `main`** when `server.py` was rewritten during the monorepo restructure.
This design **ports that proven implementation forward** onto current `main`
(which now has 5 handlers + tools the old branch lacked).

## Goal

Add a `streamable-http` transport option to greennode-mcp, with an optional
API-key Bearer guard, keeping **stdio as the default** (no behavior change for
existing local users). This is the one prerequisite to deploy greennode-mcp
(e.g., in VKS) and register its URL in the MCP Gateway.

## Non-goals

- No OAuth Authorization Code provider (Gateway handles inbound auth).
- No 3LO per-user token propagation (Gateway concern; deferred).
- No deployment manifests / VKS wiring (infrastructure, separate task).
- No changes to tools, handlers, or VKS client-credentials auth.

## Auth decision

Gateway → greennode outbound auth = **API Key** (matches the proven branch
implementation). greennode verifies `Authorization: Bearer <key>` using
constant-time comparison. The key is supplied via `--api-key` or env
`GRN_MCP_API_KEY`. For an initial test, the Gateway may use "No authentication"
outbound and rely on private networking; the API-key guard is opt-in.

## Components (ported from 4ea0522, adapted to current main/server.py)

### 1. CLI (`_build_parser()` refactor)
Refactor the inline argparse in `main()` into a `_build_parser()` returning the
parser (testable). Keep existing `--allow-write` / `--allow-sensitive-data-access`.
Add:
- `--transport {stdio,streamable-http}` (default `stdio`)
- `--host` (default `127.0.0.1`)
- `--port` (int, default `8000`)
- `--api-key` (default `None`; env fallback `GRN_MCP_API_KEY`)

### 2. `BearerTokenMiddleware` (Starlette `BaseHTTPMiddleware`)
Verbatim from the branch: validates `Authorization: Bearer <api_key>` via
`hmac.compare_digest`; returns 401 with `WWW-Authenticate: Bearer` on mismatch.
Starlette is already available (mcp dependency) — no new dep for the middleware.

### 3. Transport branch in `main()`
After registering all 5 handlers (unchanged), replace the bare `mcp.run()` with:
- `stdio` → `mcp.run()` (default, unchanged).
- `streamable-http` →
  - `import uvicorn` (optional dep; only needed for this mode).
  - Warn to stderr if no api-key ("unauthenticated; use only on trusted network").
  - `mcp.settings.host/port = args.host/args.port`.
  - For non-loopback host, set `TransportSecuritySettings(enable_dns_rebinding_protection=False)` (auth handled by api-key / private network).
  - `app = mcp.streamable_http_app()`; if api-key, `app.add_middleware(BearerTokenMiddleware, api_key=...)`.
  - `uvicorn.Server(uvicorn.Config(app, host, port, log_level="info"))` → `asyncio.run(server.serve())`.

Imports to add: `asyncio`, `hmac`, `os`, `sys`, and starlette
`BaseHTTPMiddleware`/`Request`/`Response`.

### 4. Packaging
Add an optional dependency group to `src/vks-mcp-server/pyproject.toml`:
```toml
[project.optional-dependencies]
http = ["uvicorn>=0.30.0"]
```
(Runtime dep only for streamable-http mode; stdio and tests don't need it.)

## Testing (`tests/test_server.py`, ported + adapted)

- `_build_parser().parse_args([...])`:
  - default transport == "stdio"; default host 127.0.0.1, port 8000.
  - `--transport streamable-http --host 0.0.0.0 --port 9000` parsed correctly.
  - invalid `--transport sse` → SystemExit (argparse rejects the choice).
- `BearerTokenMiddleware` (mount on a tiny Starlette app via `starlette.testclient.TestClient`, or unit-test `dispatch`):
  - correct `Authorization: Bearer <key>` → 200/passes.
  - wrong key and missing header → 401.
- Existing suite stays green; stdio path unchanged.

Run: `cd src/vks-mcp-server && uv run pytest tests/ -v`.

## Docs

- README.md / CLAUDE.md: document the `--transport streamable-http --host --port --api-key`
  flags and the "behind MCP Gateway" deployment note.
- CHANGELOG.md: Added — streamable-http transport + API-key guard.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| uvicorn missing in stdio/test envs | Import inside the streamable-http branch only; optional dep |
| Binding non-loopback without auth | Warn on stderr; recommend api-key or private network; DNS-rebinding handled |
| Drift from the old branch's handler set | Port only transport/middleware; keep current main's 5-handler registration |
| Re-regression | test_server.py guards arg parsing + middleware |

## Reference

`feat/mcp-streamable-http-transport` @ `4ea0522` — original implementation
(server.py transport block + BearerTokenMiddleware + test_server.py).
