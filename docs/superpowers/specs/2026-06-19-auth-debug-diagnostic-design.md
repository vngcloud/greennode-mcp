# Design: `--auth-debug` diagnostic (measure the Gateway 3LO contract)

Date: 2026-06-19

## Context

Phase 2 of multi-tenant auth (per-user VKS via the VNG MCP Gateway 3LO flow) is
**blocked**: the docs do not specify what the Gateway actually sends to a
downstream MCP server in a 3LO (user-federation) flow — which token/claims reach
`/mcp`, whether an end-user identity (`sub`) is propagated, what `audience` is
set, and whether/how a per-user VKS credential is minted. Designing Phase 2 from
guesses risks the token-passthrough anti-pattern and a wrong-audience design.

Rather than guess, **measure**: deploy greennode behind the Gateway with a
diagnostic enabled, drive a real 3LO call, and read back exactly what arrived.
This spec defines that diagnostic.

This is a **temporary, opt-in diagnostic**, not an auth mechanism. Phase 1's
`jwt` mode (verify + PRM + 401) remains the real auth path. This tool only
observes; it never grants or denies access.

## Goal

Add an opt-in `--auth-debug` capability to the HTTP transport that reveals, for
each inbound request, exactly what the Gateway sends — **without verifying** the
token and **without logging the full token** — via two surfaces:

1. **`AuthDebugMiddleware`** — logs a structured summary of every inbound request
   to stderr (reliably captures the real `/mcp` request the Gateway makes).
2. **`/whoami`** — an unauthenticated debug endpoint that echoes the same parsed
   summary as JSON (convenient to curl, if the Gateway forwards the path).

Both are registered **only when `--auth-debug` is on** (default off).

## Non-goals

- Not auth: does not verify signatures, does not allow/deny, does not change
  `none`/`api-key`/`jwt` behavior. `--auth-debug` is orthogonal to `--auth-mode`
  and can combine with any of them.
- Not permanent: intended to be enabled briefly during Phase 2 discovery, then
  turned off (left in the codebase as a diagnostic, off by default).
- No VKS-credential changes (that is Phase 2 proper).

## What it inspects (per request)

For each inbound HTTP request, compute a **safe summary dict**:

- `method`, `path`
- `has_authorization`: bool; `auth_scheme`: e.g. `"Bearer"` / `None`
- `token_present`: bool; `token_len`: int; `token_prefix`: first **6** chars only
  (never the full token)
- If a Bearer JWT (three dot-separated segments) — **decode WITHOUT signature
  verification** (`jwt.decode(..., options={"verify_signature": False})`):
  - `jwt_header`: `{alg, kid, typ}` (whatever is present)
  - `jwt_claims`: a **redacted** subset — `iss`, `aud`, `sub`, `azp`, `client_id`,
    `scope`, `exp`, `iat`. (Allow-list, not the whole payload, to avoid dumping
    unknown sensitive claims.)
  - If decode fails: `jwt_decode_error: "<exception class name>"` (message only,
    no token).
- `forwarding_headers`: all request headers whose name (case-insensitive) starts
  with `x-greennode-`, `x-grn-`, `x-forwarded-`, or is `x-user-id` / `x-tenant-id`
  / `forwarded` — captured verbatim (these are the Gateway's identity-propagation
  candidates we are hunting for).

The same summary feeds both the middleware log line and the `/whoami` response.

## Components

### `auth_debug.py` (new module)

Pure, dependency-light helpers — easy to unit test in isolation:

```python
def summarize_request(method: str, path: str, headers: Mapping[str, str]) -> dict:
    """Build a safe, redacted summary of an inbound request's auth surface.

    Never includes the full bearer token. JWTs are decoded WITHOUT signature
    verification (diagnostic only). Returns a JSON-serializable dict.
    """
```

Internals:
- `_redact_token(token) -> (prefix, length)` — `token[:6]`, `len(token)`.
- `_decode_jwt_unverified(token) -> (header, claims) | error` — uses
  `jwt.get_unverified_header` + `jwt.decode(token, options={"verify_signature":
  False})`, then filters claims through the allow-list.
- `_collect_forwarding_headers(headers) -> dict` — prefix/name match.

`summarize_request` must not raise: any parsing problem is captured as a field,
never propagated (a diagnostic that crashes the request defeats the purpose).

### `AuthDebugMiddleware` (in `server.py`, near `BearerTokenMiddleware`)

`BaseHTTPMiddleware` subclass. In `dispatch`: build the summary via
`summarize_request`, log it as a single line (`logger.info` with a clear
`AUTH-DEBUG` prefix, or JSON), then `await call_next(request)` unchanged. It
**never** blocks a request. It does **not** exempt `/health` from logging (a
`/health` log line is harmless and confirms the probe path), but `/health`
remains unauthenticated regardless.

### `/whoami` route (in `create_server`, conditional)

When `auth_debug` is on, register a `@server.custom_route("/whoami",
methods=["GET"])` that returns `JSONResponse(summarize_request(...))`. Like
`/health`, custom routes are not auth-wrapped, so it is reachable for probing.
Registered only when `auth_debug=True` so it never exists in normal operation.

### Wiring

- `create_server(jwt_config=None, auth_debug=False)` — new `auth_debug` param;
  registers `/whoami` only when true. `/health` registration unchanged.
- `_build_parser()`: add `--auth-debug` (`BooleanOptionalAction`, default
  `False`; env `GRN_MCP_AUTH_DEBUG` — truthy values `1/true/yes/on`).
- `main()`: resolve `auth_debug` from args/env; pass to `create_server`; in the
  streamable-http branch, `add_middleware(AuthDebugMiddleware)` when on. When on,
  print a prominent stderr warning: `"Warning: --auth-debug is ON. Request auth
  metadata (redacted) is logged and /whoami is exposed. Diagnostic only — do NOT
  enable in production."`
- stdio transport: `--auth-debug` has no effect (HTTP-only); if set with stdio,
  print a one-line note that it is ignored.

## Safety constraints (hard requirements)

1. **Never log or echo the full token** — only `token_prefix` (6 chars) +
   `token_len`.
2. **Never verify** — decode is `verify_signature=False`; this is observation,
   not trust. Output must not be mistaken for a validated identity.
3. **Opt-in, default off** — absent the flag/env, no middleware, no `/whoami`,
   zero behavior change.
4. **Claims allow-list** — only the enumerated claims are emitted, so an unknown
   sensitive claim is not dumped.
5. **Must not crash requests** — `summarize_request` swallows its own errors into
   fields; middleware always calls `call_next`.

## Behavior matrix

| `--auth-debug` | transport | Middleware logs | `/whoami` |
|---|---|---|---|
| off (default) | any | no | not registered (404) |
| on | streamable-http | yes (every request) | 200 JSON summary |
| on | stdio | n/a (ignored, note printed) | n/a |

Combines with any `--auth-mode`: e.g. `--auth-mode none --auth-debug` (observe
raw Gateway traffic) or `--auth-mode jwt --auth-debug` (observe alongside real
verification).

## Testing

`tests/test_auth_debug.py` (new):
- `summarize_request` with a Bearer JWT (signed test key, but decoded unverified)
  → header has `alg`/`kid`; claims contain the allow-listed fields; **assert the
  full token never appears** anywhere in the returned dict (only 6-char prefix);
  `token_len` correct.
- Expired / wrong-issuer JWT still summarizes fine (no verification → still
  decodes; proves we observe rather than reject).
- Malformed token (`"Bearer not.a.jwt"`) → `jwt_decode_error` present, no crash.
- No `Authorization` header → `has_authorization=False`, no token fields, no
  crash.
- Forwarding-header capture: `X-GreenNode-User`, `X-Forwarded-For`, `X-User-Id`
  captured; unrelated header (`Accept`) not captured.
- Claims allow-list: an extra claim (`"ssn": "..."`) in the JWT is **not**
  present in the output.

`tests/test_server.py` (extend):
- `create_server(auth_debug=True).streamable_http_app()` + `TestClient`: GET
  `/whoami` with a Bearer JWT → 200, JSON body contains `jwt_claims`, body does
  not contain the full token string.
- `create_server()` (default) → GET `/whoami` → 404 (not registered).
- `_build_parser()` parses `--auth-debug` / `--no-auth-debug`; env
  `GRN_MCP_AUTH_DEBUG=1` honored in resolution.
- Existing none/api-key/jwt and `/health` tests stay green (no regression).

Run from `src/vks-mcp-server`: `uv run pytest tests/ -v`;
`uv run ruff check . && uv run ruff format --check .`.

## Dependencies

None new — `pyjwt[crypto]` is already in the `http` extra (added in Phase 1);
`jwt.get_unverified_header` / `decode(verify_signature=False)` need no crypto.

## Docs

- README / CLAUDE.md: short "Diagnostics" note — `--auth-debug` is a temporary,
  opt-in tool to inspect what an upstream (e.g. the MCP Gateway) sends; redacted,
  never verifies, off by default, not for production.
- CHANGELOG: Added — `--auth-debug` diagnostic (request auth summary log +
  `/whoami`), opt-in, redacted.

## How it unblocks Phase 2

After deploying with `--auth-debug` and driving a real 3LO call through the
Gateway, the captured summary answers the three open questions:
1. **End-user identity propagation** — is there a `sub`/`X-*-User` for the human?
2. **Audience** — what `aud` does the Gateway's outbound token carry?
3. **VKS credential minting** — any header/claim that maps to a per-user VKS
   credential, or none (→ greennode must mint).

Those measurements become the inputs to the Phase 2 design.

## Reference

- `auth-mcp.md` (token passthrough anti-pattern — why we must NOT trust/forward),
  `author.md` (OAuth 2.1 / claims). Phase 1 design:
  `2026-06-19-jwt-resource-server-design.md`.
