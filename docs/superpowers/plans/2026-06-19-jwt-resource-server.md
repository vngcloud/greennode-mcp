# JWT-verify Resource Server (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a spec-compliant `jwt` inbound-auth mode that makes greennode-mcp an OAuth 2.1 Resource Server (verify Bearer JWT via JWKS, emit 401 + WWW-Authenticate + Protected Resource Metadata), selectable alongside the existing `none` and `api-key` modes.

**Architecture:** Use the mcp SDK's native auth: `FastMCP(name, token_verifier=<JwtTokenVerifier>, auth=AuthSettings(issuer_url, resource_server_url, required_scopes))` — the SDK does 401/PRM/Bearer enforcement; we only implement `TokenVerifier.verify_token` (JWT decode against the issuer's JWKS). VKS upstream still uses the global service-account (per-user is Phase 2, deferred).

**Tech Stack:** Python, mcp 1.28.0 (`mcp.server.auth`), FastMCP, PyJWT (`pyjwt[crypto]`), pytest, ruff, uv workspace.

**Spec:** `docs/superpowers/specs/2026-06-19-jwt-resource-server-design.md`

Work in `src/vks-mcp-server`; run tests `cd src/vks-mcp-server && uv run pytest`. Commit ONLY the files named in each task (never `git add -A`). After each code task also run `uv run ruff check . && uv run ruff format --check .` and fix.

---

## File structure
- Create: `src/vks-mcp-server/greennode/vks_mcp_server/auth_verifier.py` — `JwtAuthConfig` dataclass + `JwtTokenVerifier` (the only auth logic).
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/server.py` — CLI args, `_resolve_auth`, `create_server(jwt_config)`, `main()` wiring.
- Modify: `src/vks-mcp-server/pyproject.toml` — add `pyjwt[crypto]` to the `http` extra.
- Create: `src/vks-mcp-server/tests/test_auth_verifier.py`
- Modify: `src/vks-mcp-server/tests/test_server.py` — config + 401 tests.
- Modify: `CLAUDE.md`, `src/vks-mcp-server/README.md`, `src/vks-mcp-server/CHANGELOG.md`.

---

## Task 1: Dependency + JwtTokenVerifier (TDD)

**Files:**
- Modify: `src/vks-mcp-server/pyproject.toml`
- Create: `src/vks-mcp-server/greennode/vks_mcp_server/auth_verifier.py`
- Create: `src/vks-mcp-server/tests/test_auth_verifier.py`

- [ ] **Step 1: Add the dependency**

In `src/vks-mcp-server/pyproject.toml`, the `[project.optional-dependencies]` table has:
```toml
[project.optional-dependencies]
http = ["uvicorn>=0.30.0"]
```
Change it to:
```toml
[project.optional-dependencies]
http = ["uvicorn>=0.30.0", "pyjwt[crypto]>=2.8.0"]
```
Then run `uv sync --all-extras --all-groups` (from repo root) so `jwt` + `cryptography` are installed.

- [ ] **Step 2: Write the failing test** — `src/vks-mcp-server/tests/test_auth_verifier.py`

```python
"""Tests for the JWT Bearer token verifier."""
from __future__ import annotations

import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from greennode.vks_mcp_server.auth_verifier import JwtAuthConfig, JwtTokenVerifier

ISSUER = "https://iam.example.com"
AUDIENCE = "vks-mcp"


@pytest.fixture
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def verifier(rsa_key, monkeypatch):
    cfg = JwtAuthConfig(
        issuer=ISSUER,
        jwks_uri="https://iam.example.com/jwks",
        audience=AUDIENCE,
        resource_url="https://mcp.example.com/mcp",
    )
    v = JwtTokenVerifier(cfg)
    # Avoid network: return a signing key wrapping our test public key.
    pub = rsa_key.public_key()
    monkeypatch.setattr(
        v._jwks_client,
        "get_signing_key_from_jwt",
        lambda token: SimpleNamespace(key=pub),
    )
    return v


def _make_token(rsa_key, **overrides):
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-123",
        "scope": "mcp:use mcp:tools",
        "exp": int(time.time()) + 3600,
    }
    claims.update(overrides)
    return jwt.encode(claims, rsa_key, algorithm="RS256")


@pytest.mark.asyncio
async def test_valid_token_returns_access_token(verifier, rsa_key):
    token = _make_token(rsa_key)
    result = await verifier.verify_token(token)
    assert result is not None
    assert result.subject == "user-123"
    assert set(result.scopes) == {"mcp:use", "mcp:tools"}
    assert result.claims["iss"] == ISSUER


@pytest.mark.asyncio
async def test_wrong_audience_rejected(verifier, rsa_key):
    token = _make_token(rsa_key, aud="someone-else")
    assert await verifier.verify_token(token) is None


@pytest.mark.asyncio
async def test_wrong_issuer_rejected(verifier, rsa_key):
    token = _make_token(rsa_key, iss="https://evil.example.com")
    assert await verifier.verify_token(token) is None


@pytest.mark.asyncio
async def test_expired_token_rejected(verifier, rsa_key):
    token = _make_token(rsa_key, exp=int(time.time()) - 10)
    assert await verifier.verify_token(token) is None


@pytest.mark.asyncio
async def test_tampered_signature_rejected(verifier, rsa_key):
    token = _make_token(rsa_key) + "tamper"
    assert await verifier.verify_token(token) is None
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd src/vks-mcp-server && uv run pytest tests/test_auth_verifier.py -v`
Expected: FAIL — `ModuleNotFoundError: greennode.vks_mcp_server.auth_verifier`.

- [ ] **Step 4: Implement** — `src/vks-mcp-server/greennode/vks_mcp_server/auth_verifier.py`

```python
"""JWT Bearer-token verification for the streamable-http Resource Server.

Used only in `--auth-mode jwt`: validates that an inbound Bearer token is a JWT
issued by the configured issuer, for this server (audience), and unexpired.
"""
from __future__ import annotations

from dataclasses import dataclass

import jwt
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken, TokenVerifier


@dataclass
class JwtAuthConfig:
    """Configuration for JWT verification (from CLI/env)."""

    issuer: str
    jwks_uri: str
    audience: str
    resource_url: str
    required_scopes: list[str] | None = None


class JwtTokenVerifier(TokenVerifier):
    """Verify a Bearer JWT against the issuer's JWKS and expose its claims."""

    def __init__(self, config: JwtAuthConfig) -> None:
        self._config = config
        self._jwks_client = PyJWKClient(config.jwks_uri)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self._config.audience,
                issuer=self._config.issuer,
            )
        except Exception:
            return None

        scope = claims.get("scope", "")
        scopes = scope.split() if isinstance(scope, str) else list(scope or [])
        return AccessToken(
            token=token,
            client_id=claims.get("azp") or claims.get("client_id") or claims.get("sub", ""),
            scopes=scopes,
            expires_at=claims.get("exp"),
            subject=claims.get("sub"),
            claims=claims,
        )
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd src/vks-mcp-server && uv run pytest tests/test_auth_verifier.py -v`
Expected: 5 PASS.

- [ ] **Step 6: Lint + commit**

```bash
cd src/vks-mcp-server && uv run ruff check . && uv run ruff format --check .
cd /Users/lap16104/Documents/vks-skill/greenode-mcp
git add src/vks-mcp-server/pyproject.toml uv.lock \
        src/vks-mcp-server/greennode/vks_mcp_server/auth_verifier.py \
        src/vks-mcp-server/tests/test_auth_verifier.py
git commit -m "feat(auth): add JwtTokenVerifier (JWKS-based JWT verification)"
```

---

## Task 2: Auth config resolution + CLI args (TDD)

**Files:**
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/server.py` (`_build_parser`, add `_resolve_auth`)
- Modify: `src/vks-mcp-server/tests/test_server.py`

- [ ] **Step 1: Write failing tests** — append to `src/vks-mcp-server/tests/test_server.py`

```python
from greennode.vks_mcp_server.server import _resolve_auth  # noqa: E402


def _args(**kw):
    base = dict(
        auth_mode=None, api_key=None, jwt_issuer=None, jwt_jwks_uri=None,
        jwt_audience=None, jwt_required_scopes=None, resource_url=None,
    )
    base.update(kw)
    return argparse.Namespace(**base)


def test_resolve_auth_defaults_to_none(monkeypatch):
    monkeypatch.delenv("GRN_MCP_AUTH_MODE", raising=False)
    mode, jwt_config, api_key = _resolve_auth(_args())
    assert mode == "none"
    assert jwt_config is None


def test_resolve_auth_api_key_from_env(monkeypatch):
    monkeypatch.setenv("GRN_MCP_API_KEY", "secret")
    mode, jwt_config, api_key = _resolve_auth(_args(auth_mode="api-key"))
    assert mode == "api-key"
    assert api_key == "secret"
    assert jwt_config is None


def test_resolve_auth_jwt_builds_config():
    a = _args(
        auth_mode="jwt", jwt_issuer="https://iam.example.com",
        jwt_jwks_uri="https://iam.example.com/jwks", jwt_audience="vks-mcp",
        resource_url="https://mcp.example.com/mcp", jwt_required_scopes="mcp:use, mcp:tools",
    )
    mode, jwt_config, _ = _resolve_auth(a)
    assert mode == "jwt"
    assert jwt_config is not None
    assert jwt_config.issuer == "https://iam.example.com"
    assert jwt_config.audience == "vks-mcp"
    assert jwt_config.required_scopes == ["mcp:use", "mcp:tools"]


def test_resolve_auth_jwt_missing_required_exits():
    a = _args(auth_mode="jwt", jwt_issuer="https://iam.example.com")  # missing jwks/aud/resource
    with pytest.raises(SystemExit):
        _resolve_auth(a)
```

- [ ] **Step 2: Run to verify fail**

Run: `cd src/vks-mcp-server && uv run pytest tests/test_server.py -k resolve_auth -v`
Expected: FAIL — `cannot import name '_resolve_auth'`.

- [ ] **Step 3: Add CLI args to `_build_parser`**

In `server.py` `_build_parser()`, before `return parser`, add:
```python
    parser.add_argument(
        "--auth-mode",
        choices=["none", "api-key", "jwt"],
        default=None,
        help="Inbound auth for HTTP transport: none (default), api-key, or jwt "
        "(env: GRN_MCP_AUTH_MODE)",
    )
    parser.add_argument("--jwt-issuer", default=None, help="JWT issuer (env: GRN_MCP_JWT_ISSUER)")
    parser.add_argument(
        "--jwt-jwks-uri", default=None, help="JWKS URI (env: GRN_MCP_JWT_JWKS_URI)"
    )
    parser.add_argument(
        "--jwt-audience", default=None, help="Expected JWT audience (env: GRN_MCP_JWT_AUDIENCE)"
    )
    parser.add_argument(
        "--jwt-required-scopes",
        default=None,
        help="Comma-separated required scopes (env: GRN_MCP_JWT_REQUIRED_SCOPES)",
    )
    parser.add_argument(
        "--resource-url",
        default=None,
        help="This server's public URL for PRM 'resource' (env: GRN_MCP_RESOURCE_URL)",
    )
```

- [ ] **Step 4: Add `_resolve_auth`**

In `server.py`, add an import near the top (with the other greennode imports):
```python
from greennode.vks_mcp_server.auth_verifier import JwtAuthConfig, JwtTokenVerifier
```
Then add this function (place it above `create_server`):
```python
def _resolve_auth(args) -> tuple[str, JwtAuthConfig | None, str | None]:
    """Resolve inbound-auth config from CLI args + env. Returns (mode, jwt_config, api_key)."""
    mode = args.auth_mode or os.environ.get("GRN_MCP_AUTH_MODE") or "none"
    api_key = args.api_key or os.environ.get("GRN_MCP_API_KEY")
    jwt_config: JwtAuthConfig | None = None
    if mode == "jwt":
        issuer = args.jwt_issuer or os.environ.get("GRN_MCP_JWT_ISSUER")
        jwks_uri = args.jwt_jwks_uri or os.environ.get("GRN_MCP_JWT_JWKS_URI")
        audience = args.jwt_audience or os.environ.get("GRN_MCP_JWT_AUDIENCE")
        resource_url = args.resource_url or os.environ.get("GRN_MCP_RESOURCE_URL")
        missing = [
            name
            for name, val in [
                ("--jwt-issuer", issuer),
                ("--jwt-jwks-uri", jwks_uri),
                ("--jwt-audience", audience),
                ("--resource-url", resource_url),
            ]
            if not val
        ]
        if missing:
            raise SystemExit(f"--auth-mode jwt requires: {', '.join(missing)}")
        scopes_raw = args.jwt_required_scopes or os.environ.get("GRN_MCP_JWT_REQUIRED_SCOPES")
        required_scopes = (
            [s.strip() for s in scopes_raw.split(",") if s.strip()] if scopes_raw else None
        )
        jwt_config = JwtAuthConfig(
            issuer=issuer,
            jwks_uri=jwks_uri,
            audience=audience,
            resource_url=resource_url,
            required_scopes=required_scopes,
        )
    return mode, jwt_config, api_key
```
(`os` is already imported in server.py.)

- [ ] **Step 5: Run to verify pass**

Run: `cd src/vks-mcp-server && uv run pytest tests/test_server.py -k resolve_auth -v`
Expected: 4 PASS.

- [ ] **Step 6: Lint + commit**

```bash
cd src/vks-mcp-server && uv run ruff check . && uv run ruff format --check .
cd /Users/lap16104/Documents/vks-skill/greenode-mcp
git add src/vks-mcp-server/greennode/vks_mcp_server/server.py src/vks-mcp-server/tests/test_server.py
git commit -m "feat(auth): --auth-mode CLI/env resolution (none|api-key|jwt)"
```

---

## Task 3: Wire jwt mode into create_server + main (TDD)

**Files:**
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/server.py` (`create_server`, `main`)
- Modify: `src/vks-mcp-server/tests/test_server.py`

- [ ] **Step 1: Write failing tests** — append to `src/vks-mcp-server/tests/test_server.py`

```python
def _jwt_config():
    from greennode.vks_mcp_server.auth_verifier import JwtAuthConfig

    return JwtAuthConfig(
        issuer="https://iam.example.com",
        jwks_uri="https://iam.example.com/jwks",
        audience="vks-mcp",
        resource_url="https://mcp.example.com/mcp",
    )


def test_jwt_mode_protects_mcp_endpoint():
    app = create_server(_jwt_config()).streamable_http_app()
    client = TestClient(app, raise_server_exceptions=False)
    # No Bearer token -> SDK Resource Server returns 401 with WWW-Authenticate.
    r = client.get("/mcp")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_jwt_mode_health_still_open():
    app = create_server(_jwt_config()).streamable_http_app()
    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/health").status_code == 200


def test_no_auth_mode_mcp_not_401():
    app = create_server().streamable_http_app()
    client = TestClient(app, raise_server_exceptions=False)
    # Without auth, /mcp must NOT be 401 (it may be 400/406/4xx for a bad MCP request, just not 401).
    assert client.get("/mcp").status_code != 401
```

- [ ] **Step 2: Run to verify fail**

Run: `cd src/vks-mcp-server && uv run pytest tests/test_server.py -k "jwt_mode or no_auth_mode" -v`
Expected: FAIL — `create_server()` currently takes no args (TypeError) / no auth wiring.

- [ ] **Step 3: Update `create_server`**

Replace the current `create_server` in `server.py`:
```python
def create_server() -> FastMCP:
    """Create and return a FastMCP server instance."""
    server = FastMCP("vks-mcp-server", instructions=SERVER_INSTRUCTIONS)

    @server.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> Response:
        """Liveness/readiness probe endpoint (no authentication required)."""
        return JSONResponse({"status": "ok"})

    return server
```
with:
```python
def create_server(jwt_config: JwtAuthConfig | None = None) -> FastMCP:
    """Create and return a FastMCP server instance.

    When jwt_config is provided, the server runs as an OAuth 2.1 Resource Server
    (verify Bearer JWT + emit 401/WWW-Authenticate + Protected Resource Metadata).
    """
    if jwt_config is not None:
        from mcp.server.auth.settings import AuthSettings

        server = FastMCP(
            "vks-mcp-server",
            instructions=SERVER_INSTRUCTIONS,
            token_verifier=JwtTokenVerifier(jwt_config),
            auth=AuthSettings(
                issuer_url=jwt_config.issuer,
                resource_server_url=jwt_config.resource_url,
                required_scopes=jwt_config.required_scopes or None,
            ),
        )
    else:
        server = FastMCP("vks-mcp-server", instructions=SERVER_INSTRUCTIONS)

    @server.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> Response:
        """Liveness/readiness probe endpoint (no authentication required)."""
        return JSONResponse({"status": "ok"})

    return server
```

- [ ] **Step 4: Update `main()` to use the resolved auth**

In `main()`, the current top is:
```python
    args = _build_parser().parse_args()
    api_key = args.api_key or os.environ.get("GRN_MCP_API_KEY")

    config = load_config(CONFIG_PATH)
    token_manager = TokenManager(config)
    client = VksClient(config, token_manager)

    mcp = create_server()
```
Replace with:
```python
    args = _build_parser().parse_args()
    auth_mode, jwt_config, api_key = _resolve_auth(args)

    config = load_config(CONFIG_PATH)
    token_manager = TokenManager(config)
    client = VksClient(config, token_manager)

    mcp = create_server(jwt_config)
```
Then, in the `else` (streamable-http) branch, the existing api-key middleware block must only apply in `api-key` mode. Find:
```python
        starlette_app = mcp.streamable_http_app()
        if api_key:
            starlette_app.add_middleware(BearerTokenMiddleware, api_key=api_key)
```
Replace with:
```python
        starlette_app = mcp.streamable_http_app()
        if auth_mode == "api-key" and api_key:
            starlette_app.add_middleware(BearerTokenMiddleware, api_key=api_key)
```
Also update the existing "no api-key" warning so it only fires for `none` mode. Find the warning block:
```python
        if not api_key:
            print(
                "Warning: --api-key not set. Server is unauthenticated. "
                "Only use in a trusted network.",
                file=sys.stderr,
            )
```
Replace with:
```python
        if auth_mode == "none":
            print(
                "Warning: --auth-mode is 'none'. The HTTP endpoint is unauthenticated. "
                "Use api-key or jwt, or run only on a trusted network.",
                file=sys.stderr,
            )
```
(jwt-mode 401/PRM is handled inside FastMCP via create_server; no middleware needed in that branch.)

- [ ] **Step 5: Run to verify pass**

Run: `cd src/vks-mcp-server && uv run pytest tests/test_server.py -v`
Expected: all PASS (existing + new jwt/no-auth tests).

- [ ] **Step 6: Run full suite + lint**

Run: `cd src/vks-mcp-server && uv run pytest tests/ -q` → all pass.
Run: `cd src/vks-mcp-server && uv run ruff check . && uv run ruff format --check .` → clean.

- [ ] **Step 7: Commit**

```bash
cd /Users/lap16104/Documents/vks-skill/greenode-mcp
git add src/vks-mcp-server/greennode/vks_mcp_server/server.py src/vks-mcp-server/tests/test_server.py
git commit -m "feat(auth): jwt Resource Server mode (FastMCP token_verifier + AuthSettings)"
```

---

## Task 4: Documentation

**Files:**
- Modify: `CLAUDE.md`, `src/vks-mcp-server/README.md`, `src/vks-mcp-server/CHANGELOG.md`

- [ ] **Step 1: CHANGELOG** — under `## [Unreleased]` → `### Added` in `src/vks-mcp-server/CHANGELOG.md`, add:
```markdown
- Inbound auth modes for the HTTP transport via `--auth-mode none|api-key|jwt`. `jwt` makes the server an OAuth 2.1 Resource Server: verifies Bearer JWTs against a JWKS (`--jwt-issuer/--jwt-jwks-uri/--jwt-audience/--resource-url`) and emits 401 + WWW-Authenticate + Protected Resource Metadata. `/health` stays unauthenticated.
```

- [ ] **Step 2: README** — in `src/vks-mcp-server/README.md`, under the Running section, add a short subsection:
```markdown
### Inbound authentication (HTTP transport)

`--auth-mode` selects how clients authenticate to the HTTP endpoint:

- `none` (default) — no auth (use only on a trusted/private network)
- `api-key` — static Bearer token (`--api-key` / `GRN_MCP_API_KEY`)
- `jwt` — OAuth 2.1 Resource Server: verifies Bearer JWTs against a JWKS and
  advertises Protected Resource Metadata. Requires `--jwt-issuer`,
  `--jwt-jwks-uri`, `--jwt-audience`, `--resource-url` (or the matching
  `GRN_MCP_JWT_*` / `GRN_MCP_RESOURCE_URL` env vars); optional
  `--jwt-required-scopes`.

Behind the GreenNode MCP Gateway: use `api-key` when the Gateway's outbound auth
is API Key, or `jwt` when it is OAuth 2.0. (Per-user VKS access is a future phase.)
```

- [ ] **Step 3: CLAUDE.md** — add a brief note under an appropriate section (e.g. after "Server flags"):
```markdown
## Inbound auth (HTTP transport)

`--auth-mode none|api-key|jwt`. `jwt` runs the server as an OAuth 2.1 Resource Server
(`token_verifier` + `AuthSettings` → 401 + WWW-Authenticate + PRM), verifying Bearer
JWTs via JWKS (`--jwt-issuer/--jwt-jwks-uri/--jwt-audience/--resource-url`). VKS upstream
still uses the global service account (per-user is a future phase). `/health` is always open.
```

- [ ] **Step 4: Run full suite + commit**

Run: `cd src/vks-mcp-server && uv run pytest tests/ -q` → all pass.
```bash
cd /Users/lap16104/Documents/vks-skill/greenode-mcp
git add CLAUDE.md src/vks-mcp-server/README.md src/vks-mcp-server/CHANGELOG.md
git commit -m "docs: document --auth-mode (none/api-key/jwt) Resource Server"
```

---

## Notes for the implementer
- Do NOT change VKS credential handling (TokenManager/VksClient) — per-user VKS is Phase 2 and intentionally out of scope.
- `none` and `api-key` paths must behave exactly as before (regression check: existing test_server.py BearerTokenMiddleware tests still pass).
- If `mcp` `AuthSettings`/`AccessToken` field names differ from this plan in the installed version, inspect `.venv/.../mcp/server/auth/{settings.py,provider.py}` and adapt the field names (keep behavior identical); report any deviation.
