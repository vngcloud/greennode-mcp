# Design: JWT-verify Resource Server (Phase 1 of multi-tenant auth)

Date: 2026-06-19

## Context

greennode-mcp's streamable-http transport currently guards `/mcp` with only a
**static API-key** (`BearerTokenMiddleware`). To align with the MCP Authorization
spec (OAuth 2.1 — `author.md`) and security best practices (`auth-mcp.md`), the
server should be able to act as a proper **OAuth 2.1 Resource Server**: validate
Bearer **JWT** access tokens issued *for it*, and advertise discovery via
Protected Resource Metadata (PRM).

This is **Phase 1** of the multi-tenant (B2) effort. Phase 2 (per-user VKS
credentials via Gateway 3LO) is **deferred**: the Gateway→MCP-server 3LO contract
(what token/claims/credential reaches the server, whether usable for VKS, or a
Delegated API Key mapping) is **not specified** in available docs and must be
clarified first. JWT-verify already exposes per-request identity
(`get_access_token()`), which Phase 2 will build on.

SDK note: installed `mcp` is **1.28.0**. `FastMCP(name, token_verifier=...,
auth=AuthSettings(...))` natively produces 401 + `WWW-Authenticate` + PRM +
Bearer verification. `@mcp.custom_route` handlers (e.g. `/health`) are NOT
auth-wrapped (stay open). Inside tools, `get_access_token()` returns the verified
`AccessToken` (`.subject`, `.scopes`, `.claims`).

## Goal

Add a `jwt` inbound-auth mode that makes greennode a spec-compliant Resource
Server (verify JWT, PRM, 401/WWW-Authenticate), selectable alongside the existing
`none` and `api-key` modes. No per-user VKS yet (that is Phase 2).

## Non-goals (Phase 2)

- Per-user / per-request VKS credentials; mapping token claims → VKS access.
- Gateway 3LO integration; Delegated API Key.
- An in-server OAuth Authorization Server (authorize/token/DCR) — the VNG MCP
  Gateway is the authorization layer; greennode is only a Resource Server.

## Auth modes (inbound: client/Gateway → greennode)

A single `--auth-mode` selects behavior for the HTTP transport:

| `--auth-mode` | Behavior | Matches Gateway outbound = |
|---|---|---|
| `none` (default) | No inbound auth (rely on private network) | No authentication |
| `api-key` | Existing `BearerTokenMiddleware` (static shared secret, constant-time) | API Key |
| `jwt` | FastMCP Resource Server: verify Bearer JWT + PRM + 401 | OAuth 2.0 |

`none` and `api-key` preserve current behavior exactly (no regression). stdio
transport ignores auth entirely.

## Components

### `JwtTokenVerifier` (new module `auth_verifier.py`)
Implements the SDK `TokenVerifier` protocol:
```python
async def verify_token(self, token: str) -> AccessToken | None
```
- Verifies signature via a **JWKS URI** (`PyJWKClient`) — or a static public key
  if configured — plus `issuer`, `audience`, and `exp`.
- On success returns `AccessToken(token=token, client_id=<azp/client_id/sub>,
  scopes=<scope claim split>, expires_at=<exp>, subject=<sub>, claims=<all>)`.
- On any failure (bad signature/issuer/audience/expiry/parse) returns `None`
  (SDK then emits 401). No exceptions leak.
- Uses `pyjwt[crypto]`.

### `create_server(auth)` wiring
`create_server` accepts an auth config object. When mode == `jwt`:
```python
FastMCP("vks-mcp-server", instructions=...,
        token_verifier=JwtTokenVerifier(cfg),
        auth=AuthSettings(issuer_url=cfg.issuer,
                          resource_server_url=cfg.resource_url,
                          required_scopes=cfg.required_scopes or None))
```
Otherwise `FastMCP(...)` with no auth (current). The `/health` custom_route is
registered as today (stays open).

### CLI / env
Add to `_build_parser()`:
- `--auth-mode {none,api-key,jwt}` (default `none`; env `GRN_MCP_AUTH_MODE`)
- `--jwt-issuer` (env `GRN_MCP_JWT_ISSUER`)
- `--jwt-jwks-uri` (env `GRN_MCP_JWT_JWKS_URI`)
- `--jwt-audience` (env `GRN_MCP_JWT_AUDIENCE`)
- `--jwt-required-scopes` (comma-separated; env `GRN_MCP_JWT_REQUIRED_SCOPES`)
- `--resource-url` (the server's public URL for PRM `resource`; env `GRN_MCP_RESOURCE_URL`)

`main()` resolves args+env into the auth config, passes to `create_server`. For
`jwt` mode, `--jwt-issuer`, `--jwt-jwks-uri`, `--jwt-audience`, `--resource-url`
are required; missing → exit with a clear error. The existing `--api-key` /
`GRN_MCP_API_KEY` continues to drive `api-key` mode (and `BearerTokenMiddleware`
is added only in `api-key` mode).

## Behavior

- `jwt` mode, GET/POST `/mcp` without a valid Bearer JWT → **401** with
  `WWW-Authenticate: Bearer ... resource_metadata="…/.well-known/oauth-protected-resource"`
  (emitted by SDK). Valid JWT → request proceeds; tools can read
  `get_access_token()`.
- `/health` → 200 in all modes (custom_route, never auth-wrapped).
- VKS calls still use the global service-account credentials (Phase 1). The
  verified JWT is the *inbound* identity only — NOT forwarded to VKS (no token
  passthrough; audience is greennode).

## Testing

`tests/test_auth_verifier.py`:
- `verify_token` with a JWT signed by a test RSA key (via JWKS or injected key):
  valid → `AccessToken` with expected `subject`/`scopes`/`claims`; tampered
  signature, wrong `issuer`, wrong `audience`, expired → `None`.

`tests/test_server.py` (extend):
- Build `create_server(jwt-config-with-stub-verifier).streamable_http_app()`;
  `TestClient` GET `/mcp` (or POST) without token → **401**, response has a
  `WWW-Authenticate` header. (Use a stub `TokenVerifier` returning `None`/an
  `AccessToken` to avoid real JWKS in tests.)
- `/health` → 200 in jwt mode (still open).
- `_build_parser()`/config: `--auth-mode jwt` without required jwt args → error;
  `none`/`api-key` unchanged; `--auth-mode api-key` still wires `BearerTokenMiddleware`.

Keep existing tests green (none/api-key paths unchanged). Run from
`src/vks-mcp-server`: `uv run pytest tests/ -v`; `uv run ruff check . && uv run ruff format --check .`.

## Dependencies

Add `pyjwt[crypto]>=2.8.0` to `[project.optional-dependencies] http` (JWT verify
is only used in the HTTP/jwt path).

## Docs

- README / CLAUDE.md: document the `--auth-mode` flag and the three modes; note
  greennode is a Resource Server behind the MCP Gateway (Gateway does inbound
  agent auth + policy; jwt mode verifies the Gateway's OAuth outbound token).
- CHANGELOG: Added — JWT-verify Resource Server (`--auth-mode jwt`, PRM + 401).

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| JWKS fetch latency/failure at verify time | `PyJWKClient` caches keys; verify failure → 401 (fail closed), not crash |
| `AccessToken` field drift across mcp versions | Pinned mcp; test asserts the fields we set; keep verifier mapping minimal |
| Operator misconfig (wrong issuer/aud) | Required-arg validation for jwt mode + clear startup error; 401 on mismatch |
| Over-building (Phase 2 leakage) | Strictly inbound verify; no VKS-credential changes in this phase |

## Reference

- `author.md` (MCP Authorization / OAuth 2.1), `auth-mcp.md` (security best
  practices). FastMCP `token_verifier`/`AuthSettings`, `get_access_token()`,
  `TokenVerifier`/`AccessToken` in `mcp/server/auth/`.
- Cloudflare = full in-server OAuth AS (not our model); AWS = stdio+local creds
  (only `aws-api-mcp-server` does verify-only JWT — closest analog to this phase).
