# `--auth-debug` Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in `--auth-debug` capability that reveals (redacted, unverified) exactly what an upstream sends to the HTTP transport — via a request-logging middleware and a `/whoami` echo endpoint — so the Gateway 3LO contract can be measured to unblock Phase 2.

**Architecture:** A new pure module `auth_debug.py` builds a safe, JSON-serializable summary of a request's auth surface (`summarize_request`). `server.py` consumes it from `AuthDebugMiddleware` (logs every request) and a conditional `/whoami` custom route. A new `--auth-debug` flag / `GRN_MCP_AUTH_DEBUG` env (default off, HTTP-only) gates both. Orthogonal to `--auth-mode`; zero behavior change when off.

**Tech Stack:** Python, `mcp` (FastMCP) 1.28.0, Starlette `BaseHTTPMiddleware`, `pyjwt` (already present), pytest + Starlette `TestClient`. Run from `src/vks-mcp-server` with `uv run`.

---

## File Structure

- **Create** `greennode/vks_mcp_server/auth_debug.py` — pure helpers: `summarize_request` + `_redact_token`, `_decode_jwt_unverified`, `_collect_forwarding_headers`. No Starlette/MCP imports; takes plain `method/path/headers`. One responsibility: turn a request's auth surface into a safe dict.
- **Modify** `greennode/vks_mcp_server/server.py` — add `AuthDebugMiddleware`, `_env_truthy`, `auth_debug` param on `create_server`, `--auth-debug` in `_build_parser`, wiring + warnings in `main`.
- **Create** `tests/test_auth_debug.py` — unit tests for `summarize_request`.
- **Modify** `tests/test_server.py` — parser flag, `/whoami` route presence/absence, middleware behavior.
- **Modify** `README.md`, `CLAUDE.md`, `CHANGELOG.md` — short Diagnostics note + changelog entry.

All test commands run from `/Users/lap16104/Documents/vks-skill/greenode-mcp/src/vks-mcp-server`.

---

## Task 1: `auth_debug.summarize_request` core (no-auth + token redaction)

**Files:**
- Create: `src/vks-mcp-server/greennode/vks_mcp_server/auth_debug.py`
- Test: `src/vks-mcp-server/tests/test_auth_debug.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_auth_debug.py`:

```python
"""Tests for the opt-in auth-debug request summarizer."""

from __future__ import annotations

import jwt
from greennode.vks_mcp_server.auth_debug import summarize_request


def test_no_authorization_header():
    s = summarize_request("GET", "/mcp", {})
    assert s["method"] == "GET"
    assert s["path"] == "/mcp"
    assert s["has_authorization"] is False
    assert s["auth_scheme"] is None
    assert "token_prefix" not in s
    assert s["forwarding_headers"] == {}


def test_bearer_token_is_redacted_never_full():
    token = "abcdefghijklmnopqrstuvwxyz0123456789"
    s = summarize_request("POST", "/mcp", {"Authorization": f"Bearer {token}"})
    assert s["has_authorization"] is True
    assert s["auth_scheme"] == "Bearer"
    assert s["token_present"] is True
    assert s["token_len"] == len(token)
    assert s["token_prefix"] == token[:6]
    # The full token must never appear anywhere in the summary.
    assert token not in repr(s)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_auth_debug.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'greennode.vks_mcp_server.auth_debug'`

- [ ] **Step 3: Write minimal implementation**

Create `greennode/vks_mcp_server/auth_debug.py`:

```python
"""Opt-in diagnostic helpers to summarize an inbound request's auth surface.

DIAGNOSTIC ONLY. Never verifies JWT signatures and never includes the full
bearer token (only a short prefix + length). Used by the --auth-debug flag to
measure what an upstream (e.g. the MCP Gateway) actually sends downstream.
"""

from __future__ import annotations

from typing import Mapping

_TOKEN_PREFIX_LEN = 6


def _redact_token(token: str) -> dict:
    """Return non-reversible token metadata only (never the full token)."""
    return {
        "token_present": True,
        "token_len": len(token),
        "token_prefix": token[:_TOKEN_PREFIX_LEN],
    }


def summarize_request(method: str, path: str, headers: Mapping[str, str]) -> dict:
    """Build a safe, JSON-serializable summary of a request's auth surface.

    Never raises and never includes the full bearer token.
    """
    summary: dict = {"method": method, "path": path}
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    summary["has_authorization"] = bool(auth)
    if not auth:
        summary["auth_scheme"] = None
        summary["forwarding_headers"] = {}
        return summary
    parts = auth.split(" ", 1)
    summary["auth_scheme"] = parts[0]
    token = parts[1].strip() if len(parts) == 2 else ""
    if token:
        summary.update(_redact_token(token))
    summary["forwarding_headers"] = {}
    return summary
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_auth_debug.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/vks-mcp-server/greennode/vks_mcp_server/auth_debug.py src/vks-mcp-server/tests/test_auth_debug.py
git commit -m "feat: auth_debug.summarize_request core with token redaction"
```

---

## Task 2: Unverified JWT decode + claims allow-list

**Files:**
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/auth_debug.py`
- Test: `src/vks-mcp-server/tests/test_auth_debug.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_auth_debug.py`:

```python
def _hs256(**claims) -> str:
    # Signature is irrelevant: summarize_request never verifies it.
    return jwt.encode(claims, "irrelevant-secret", algorithm="HS256")


def test_jwt_header_and_allowlisted_claims():
    token = _hs256(iss="https://iam.vng", aud="vks-mcp", sub="user-7",
                   scope="mcp:use", exp=9999999999, iat=1)
    s = summarize_request("POST", "/mcp", {"Authorization": f"Bearer {token}"})
    assert s["jwt_header"]["alg"] == "HS256"
    assert s["jwt_claims"]["iss"] == "https://iam.vng"
    assert s["jwt_claims"]["aud"] == "vks-mcp"
    assert s["jwt_claims"]["sub"] == "user-7"
    assert s["jwt_claims"]["scope"] == "mcp:use"


def test_jwt_claims_allowlist_drops_unknown_sensitive_claims():
    token = _hs256(iss="i", aud="a", sub="s", ssn="123-45-6789", password="hunter2")
    s = summarize_request("POST", "/mcp", {"Authorization": f"Bearer {token}"})
    assert "ssn" not in s["jwt_claims"]
    assert "password" not in s["jwt_claims"]
    assert "ssn" not in repr(s)


def test_expired_or_wrong_issuer_jwt_still_summarizes():
    # No verification => an expired token still decodes (proves we observe, not reject).
    token = _hs256(iss="whatever", aud="x", sub="u", exp=1)
    s = summarize_request("POST", "/mcp", {"Authorization": f"Bearer {token}"})
    assert s["jwt_claims"]["exp"] == 1


def test_malformed_bearer_jwt_records_error_without_crashing():
    s = summarize_request("POST", "/mcp", {"Authorization": "Bearer not.a.jwt"})
    assert "jwt_decode_error" in s
    assert "token_prefix" in s  # still redacts the malformed token


def test_non_bearer_scheme_is_not_jwt_decoded():
    s = summarize_request("GET", "/mcp", {"Authorization": "Basic dXNlcjpwYXNz"})
    assert s["auth_scheme"] == "Basic"
    assert "jwt_header" not in s
    assert "jwt_claims" not in s
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_auth_debug.py -v`
Expected: FAIL — `KeyError: 'jwt_header'` / `KeyError: 'jwt_decode_error'` (decode not implemented yet).

- [ ] **Step 3: Write the implementation**

Edit `auth_debug.py`. Add `import jwt` to the imports:

```python
from typing import Mapping

import jwt
```

Add the allow-list constant near `_TOKEN_PREFIX_LEN`:

```python
# Allow-list of claims we surface. Anything else (incl. unknown sensitive
# claims in an unverified token) is dropped.
_CLAIM_ALLOWLIST = ("iss", "aud", "sub", "azp", "client_id", "scope", "exp", "iat")
```

Add the decode helper:

```python
def _decode_jwt_unverified(token: str) -> dict:
    """Decode a JWT WITHOUT verifying its signature (diagnostic only)."""
    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.decode(token, options={"verify_signature": False})
    except Exception as exc:  # noqa: BLE001 - a diagnostic must never propagate
        return {"jwt_decode_error": type(exc).__name__}
    return {
        "jwt_header": {k: header.get(k) for k in ("alg", "kid", "typ") if k in header},
        "jwt_claims": {k: claims[k] for k in _CLAIM_ALLOWLIST if k in claims},
    }
```

In `summarize_request`, replace the `if token:` block so a Bearer JWT is decoded:

```python
    if token:
        summary.update(_redact_token(token))
        if parts[0].lower() == "bearer" and token.count(".") == 2:
            summary.update(_decode_jwt_unverified(token))
    summary["forwarding_headers"] = {}
    return summary
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_auth_debug.py -v`
Expected: PASS (all auth_debug tests).

- [ ] **Step 5: Commit**

```bash
git add src/vks-mcp-server/greennode/vks_mcp_server/auth_debug.py src/vks-mcp-server/tests/test_auth_debug.py
git commit -m "feat: auth_debug unverified JWT decode with claims allow-list"
```

---

## Task 3: Forwarding-header capture

**Files:**
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/auth_debug.py`
- Test: `src/vks-mcp-server/tests/test_auth_debug.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_auth_debug.py`:

```python
def test_forwarding_headers_captured_case_insensitively():
    headers = {
        "X-GreenNode-User": "alice",
        "X-GRN-Tenant": "team-9",
        "X-Forwarded-For": "10.0.0.1",
        "X-User-Id": "u-42",
        "Forwarded": "for=10.0.0.1",
        "Accept": "application/json",
    }
    s = summarize_request("GET", "/mcp", headers)
    fwd = s["forwarding_headers"]
    assert fwd["x-greennode-user"] == "alice"
    assert fwd["x-grn-tenant"] == "team-9"
    assert fwd["x-forwarded-for"] == "10.0.0.1"
    assert fwd["x-user-id"] == "u-42"
    assert fwd["forwarded"] == "for=10.0.0.1"
    assert "accept" not in fwd
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth_debug.py::test_forwarding_headers_captured_case_insensitively -v`
Expected: FAIL — `forwarding_headers` is `{}` so `KeyError: 'x-greennode-user'`.

- [ ] **Step 3: Write the implementation**

Edit `auth_debug.py`. Add the match constants near `_CLAIM_ALLOWLIST`:

```python
# Header names/prefixes that may carry upstream identity propagation.
_FORWARD_PREFIXES = ("x-greennode-", "x-grn-", "x-forwarded-")
_FORWARD_NAMES = ("x-user-id", "x-tenant-id", "forwarded")
```

Add the collector:

```python
def _collect_forwarding_headers(headers: Mapping[str, str]) -> dict:
    out: dict = {}
    for name, value in headers.items():
        lname = name.lower()
        if lname.startswith(_FORWARD_PREFIXES) or lname in _FORWARD_NAMES:
            out[lname] = value
    return out
```

In `summarize_request`, replace **both** assignments `summary["forwarding_headers"] = {}` (the early-return one and the final one) with:

```python
    summary["forwarding_headers"] = _collect_forwarding_headers(headers)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_auth_debug.py -v`
Expected: PASS (all auth_debug tests).

- [ ] **Step 5: Commit**

```bash
git add src/vks-mcp-server/greennode/vks_mcp_server/auth_debug.py src/vks-mcp-server/tests/test_auth_debug.py
git commit -m "feat: auth_debug captures upstream forwarding headers"
```

---

## Task 4: `--auth-debug` CLI flag + `_env_truthy`

**Files:**
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/server.py`
- Test: `src/vks-mcp-server/tests/test_server.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_server.py` (after the existing parser tests, before the `create_server` import block is fine — these only need `_parse_args`):

```python
def test_auth_debug_defaults_to_false():
    args = _parse_args([])
    assert args.auth_debug is False


def test_auth_debug_flag_enables():
    args = _parse_args(["--auth-debug"])
    assert args.auth_debug is True


def test_no_auth_debug_flag_disables():
    args = _parse_args(["--no-auth-debug"])
    assert args.auth_debug is False


def test_env_truthy_values():
    from greennode.vks_mcp_server.server import _env_truthy

    assert _env_truthy("1") is True
    assert _env_truthy("true") is True
    assert _env_truthy("YES") is True
    assert _env_truthy("on") is True
    assert _env_truthy("0") is False
    assert _env_truthy("") is False
    assert _env_truthy(None) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_server.py -k "auth_debug or env_truthy" -v`
Expected: FAIL — `AttributeError: 'Namespace' object has no attribute 'auth_debug'` and `ImportError` for `_env_truthy`.

- [ ] **Step 3: Write the implementation**

In `server.py`, add the `--auth-debug` argument inside `_build_parser()` (after the `--resource-url` argument, before `return parser`):

```python
    parser.add_argument(
        "--auth-debug",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="DIAGNOSTIC: log redacted inbound auth summary and expose /whoami "
        "(HTTP only, off by default; env: GRN_MCP_AUTH_DEBUG). Do NOT use in production.",
    )
    return parser
```

Add `_env_truthy` near `_resolve_auth` (module-level function):

```python
def _env_truthy(val: str | None) -> bool:
    """True for common truthy env-var spellings (1/true/yes/on)."""
    return (val or "").strip().lower() in {"1", "true", "yes", "on"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_server.py -k "auth_debug or env_truthy" -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/vks-mcp-server/greennode/vks_mcp_server/server.py src/vks-mcp-server/tests/test_server.py
git commit -m "feat: --auth-debug CLI flag and _env_truthy helper"
```

---

## Task 5: `AuthDebugMiddleware`

**Files:**
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/server.py`
- Test: `src/vks-mcp-server/tests/test_server.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_server.py` (the `Starlette`/`Route`/`TestClient`/`PlainTextResponse` imports already exist at the top of the file):

```python
from greennode.vks_mcp_server.server import AuthDebugMiddleware  # noqa: E402


def test_auth_debug_middleware_passes_request_through():
    app = AuthDebugMiddleware(_inner_app)
    client = TestClient(app, raise_server_exceptions=False)
    # No Authorization header: must not block, must not crash.
    r = client.get("/")
    assert r.status_code == 200


def test_auth_debug_middleware_logs_summary(caplog):
    import logging

    app = AuthDebugMiddleware(_inner_app)
    client = TestClient(app, raise_server_exceptions=False)
    token = "abcdef1234567890abcdef"
    with caplog.at_level(logging.INFO, logger="greennode.vks_mcp_server.auth_debug"):
        client.get("/", headers={"Authorization": f"Bearer {token}"})
    logged = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "AUTH-DEBUG" in logged
    assert "abcdef"  # prefix present
    assert token not in logged  # full token never logged
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_server.py -k auth_debug_middleware -v`
Expected: FAIL — `ImportError: cannot import name 'AuthDebugMiddleware'`.

- [ ] **Step 3: Write the implementation**

In `server.py`, add imports at the top (with the other stdlib imports):

```python
import json
import logging
```

Add a module-level logger after the imports (near `CONFIG_PATH`):

```python
logger = logging.getLogger("greennode.vks_mcp_server.auth_debug")
```

Import the summarizer with the other `greennode...` imports:

```python
from greennode.vks_mcp_server.auth_debug import summarize_request
```

Add the middleware class after `BearerTokenMiddleware`:

```python
class AuthDebugMiddleware(BaseHTTPMiddleware):
    """DIAGNOSTIC: log a redacted summary of every inbound request, then pass it
    through unchanged. Never blocks a request; never logs the full bearer token.
    """

    async def dispatch(self, request: Request, call_next):
        """Log the request's redacted auth summary, then forward it untouched."""
        summary = summarize_request(request.method, request.url.path, request.headers)
        logger.info("AUTH-DEBUG %s", json.dumps(summary, default=str))
        return await call_next(request)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_server.py -k auth_debug_middleware -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/vks-mcp-server/greennode/vks_mcp_server/server.py src/vks-mcp-server/tests/test_server.py
git commit -m "feat: AuthDebugMiddleware logs redacted request auth summary"
```

---

## Task 6: `/whoami` route via `create_server(auth_debug=...)`

**Files:**
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/server.py`
- Test: `src/vks-mcp-server/tests/test_server.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_server.py` (the `create_server` import already exists earlier in the file):

```python
def test_whoami_not_registered_by_default():
    app = create_server().streamable_http_app()
    paths = [getattr(r, "path", None) for r in app.router.routes]
    assert "/whoami" not in paths


def test_whoami_registered_when_auth_debug():
    app = create_server(auth_debug=True).streamable_http_app()
    paths = [getattr(r, "path", None) for r in app.router.routes]
    assert "/whoami" in paths


def test_whoami_echoes_redacted_summary():
    import jwt

    app = create_server(auth_debug=True).streamable_http_app()
    client = TestClient(app, raise_server_exceptions=False)
    token = jwt.encode({"iss": "i", "aud": "a", "sub": "u-1"}, "x", algorithm="HS256")
    r = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["jwt_claims"]["sub"] == "u-1"
    assert body["token_prefix"] == token[:6]
    assert token not in r.text  # full token never echoed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_server.py -k whoami -v`
Expected: FAIL — `create_server()` has no `auth_debug` param → `TypeError`, and `/whoami` absent.

- [ ] **Step 3: Write the implementation**

In `server.py`, change the `create_server` signature and register `/whoami` conditionally. Update the signature line:

```python
def create_server(
    jwt_config: JwtAuthConfig | None = None, auth_debug: bool = False
) -> FastMCP:
```

Then, after the existing `/health` custom_route registration and before `return server`, add:

```python
    if auth_debug:

        @server.custom_route("/whoami", methods=["GET"])
        async def whoami(request: Request) -> Response:
            """DIAGNOSTIC: echo the request's redacted auth summary (no auth, no verify)."""
            return JSONResponse(
                summarize_request(request.method, request.url.path, request.headers)
            )

    return server
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_server.py -k whoami -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/vks-mcp-server/greennode/vks_mcp_server/server.py src/vks-mcp-server/tests/test_server.py
git commit -m "feat: conditional /whoami debug route under auth_debug"
```

---

## Task 7: Wire `auth_debug` into `main()`

**Files:**
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/server.py`

This wiring drives the real process (`create_server` + middleware + warnings). It is exercised end-to-end by the route/middleware tests above; this task connects them in `main()`.

- [ ] **Step 1: Resolve `auth_debug` and pass to `create_server`**

In `main()`, after `auth_mode, jwt_config, api_key = _resolve_auth(args)`, add:

```python
    auth_debug = args.auth_debug or _env_truthy(os.environ.get("GRN_MCP_AUTH_DEBUG"))
```

Change the server creation line from `mcp = create_server(jwt_config)` to:

```python
    mcp = create_server(jwt_config, auth_debug=auth_debug)
```

- [ ] **Step 2: Add stdio note + HTTP warning/middleware**

In the `if args.transport == "stdio":` branch, before `mcp.run()`:

```python
        if auth_debug:
            print(
                "Note: --auth-debug has no effect with stdio transport (HTTP only); ignoring.",
                file=sys.stderr,
            )
        mcp.run()
```

In the `else:` (streamable-http) branch, after `starlette_app = mcp.streamable_http_app()` and the existing api-key middleware block, add:

```python
        if auth_debug:
            print(
                "Warning: --auth-debug is ON. Redacted request auth metadata is logged "
                "and /whoami is exposed. Diagnostic only -- do NOT enable in production.",
                file=sys.stderr,
            )
            starlette_app.add_middleware(AuthDebugMiddleware)
```

- [ ] **Step 3: Verify nothing regressed**

Run: `uv run pytest tests/ -v`
Expected: PASS (all prior tests + the new auth_debug/server tests; no failures).

- [ ] **Step 4: Lint**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: no errors. If `ruff format --check` reports diffs, run `uv run ruff format .` and re-run the check.

- [ ] **Step 5: Commit**

```bash
git add src/vks-mcp-server/greennode/vks_mcp_server/server.py
git commit -m "feat: wire --auth-debug into main (middleware + warnings)"
```

---

## Task 8: Docs + changelog

**Files:**
- Modify: `README.md`, `CLAUDE.md`, `CHANGELOG.md` (repo root: `/Users/lap16104/Documents/vks-skill/greenode-mcp/`)

- [ ] **Step 1: Add a Diagnostics note to `README.md`**

Find the section documenting `--auth-mode` / HTTP transport flags and add after it:

```markdown
### Diagnostics: `--auth-debug` (temporary, opt-in)

`--auth-debug` (env `GRN_MCP_AUTH_DEBUG=1`) makes the HTTP transport log a
**redacted** summary of every inbound request and expose an unauthenticated
`GET /whoami` that echoes the same summary. It is meant for measuring what an
upstream (e.g. the MCP Gateway) actually sends — token scheme, JWT header
(`alg`/`kid`), allow-listed claims (`iss`/`aud`/`sub`/`scope`/...), and any
`X-GreenNode-*` / `X-Forwarded-*` identity headers.

It **never verifies** signatures and **never logs the full token** (only a
6-char prefix + length). It is **off by default** and **must not be enabled in
production**. It is orthogonal to `--auth-mode` and can be combined with any mode.
```

- [ ] **Step 2: Mirror the note in `CLAUDE.md`**

Add the same short paragraph under the operational/flags section of `CLAUDE.md` (one or two sentences is enough there): note that `--auth-debug` is opt-in, redacted, never verifies, HTTP-only, not for production.

- [ ] **Step 3: Add a `CHANGELOG.md` entry**

Under the top `Added` section (create an `Unreleased`/`Added` block if the file groups by version, matching the existing style):

```markdown
- `--auth-debug` diagnostic (env `GRN_MCP_AUTH_DEBUG`): logs a redacted inbound
  request auth summary and exposes `GET /whoami`. Opt-in, never verifies, never
  logs full tokens; HTTP transport only. For measuring upstream/Gateway auth.
```

- [ ] **Step 4: Verify the full suite once more**

Run: `uv run pytest tests/ -v && uv run ruff check . && uv run ruff format --check .`
Expected: all pass, no lint errors.

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md CHANGELOG.md
git commit -m "docs: document --auth-debug diagnostic"
```

---

## Self-Review (author checklist — completed)

**Spec coverage:**
- Two surfaces (middleware-log + `/whoami`) → Tasks 5, 6. ✓
- Inspect fields (method/path, has_authorization/scheme, token redaction, JWT header, allow-listed claims, forwarding headers) → Tasks 1–3. ✓
- `auth_debug.py` pure module + `summarize_request` → Tasks 1–3. ✓
- Wiring `create_server(..., auth_debug=)`, `--auth-debug`/env, stdio note, HTTP warning → Tasks 4, 6, 7. ✓
- Safety: no full token (Tasks 1,5,6 assert), no verify (Task 2), opt-in default off (Tasks 4,6), claims allow-list (Task 2), never crash (Task 1 no-auth + Task 2 malformed). ✓
- Tests (`test_auth_debug.py` + `test_server.py` extensions) → every task. ✓
- No new deps (pyjwt already present) → confirmed, no dependency task needed. ✓
- Docs + changelog → Task 8. ✓

**Placeholder scan:** none — every code/test step has concrete content.

**Type/name consistency:** `summarize_request(method, path, headers)`, `_redact_token`, `_decode_jwt_unverified`, `_collect_forwarding_headers`, `_CLAIM_ALLOWLIST`, `_FORWARD_PREFIXES`, `_FORWARD_NAMES`, `_env_truthy`, `AuthDebugMiddleware`, `create_server(jwt_config, auth_debug)` — used identically across tasks. `token_prefix` is 6 chars everywhere. Logger name `greennode.vks_mcp_server.auth_debug` matches between middleware and its test.
