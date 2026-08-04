# CLAUDE.md — Agentbase MCP Server

Product-specific guidance for `src/agentbase-mcp-server`. Monorepo-wide
conventions (tool naming, DTOs, TDD, branch/release flow, security rules) live
in the **repo-root CLAUDE.md** — read that first.

## Product overview

MCP server for the Agentbase platform (GreenNode). **Pilot scope:** the
`policy` service (12 tools). The other five services (runtime, identity,
memory, gateway, cr) will be ported service-by-service using the playbook below.

- **12 tools** across 1 handler: PolicyHandler (policy groups CRUD, policies
  CRUD, condition operators, authorization decisions).
- **Passthrough-only auth**: the server holds NO service-account credentials.
  Every upstream call forwards the caller's IAM bearer token (via
  `mcp_core.http.user_token_var`). stdio reads it from `GREENNODE_MCP_TOKEN`;
  HTTP gates each request on `Authorization: Bearer …` (401 if missing).
- **Every tool declares ToolAnnotations** (`READ`/`WRITE`/`DESTRUCTIVE`) picked
  by effect — `get_authorization_decision` is POST-but-read, so `READ`.
- **`list_condition_operators` is the only cached tool** (static reference data;
  `refresh: true` bypasses). Per-caller mutable resources (policy groups,
  policies) are never cached.

## The passthrough deviation (why no TokenManager / ~/.greennode)

This server deliberately does NOT use `mcp_core.auth.TokenManager`,
`mcp_core.config.load_profile`, or `~/.greennode`. The source Agentbase server
is an auth gateway that forwards each caller's token upstream and mints none.
The port keeps that contract. `PassthroughTokenManager` is a **guard**, not a
minter: it satisfies `BaseClient`'s `token_manager` arg and raises loudly if a
code path ever calls `get_token()` (i.e. forgot to set `user_token_var`).
`BaseClient`'s 401 path raises immediately for user tokens (never falls back),
which is correct — the server cannot refresh the *caller's* token.

## Policy API quirks

- **Pagination is 1-based**: `page` (default 1) + `page_size` (default 10). List
  tools page internally via `paging.fetch_all_agentbase_items` and never expose
  paging params to the model.
- **`get_authorization_decision` is POST-but-read** — returns an allow/deny
  decision, mutates no state. Annotated `READ`, not gated behind `--allow-write`.
  Lives under `/internal/api/v1/gateways/{gatewayName}/targets/{targetName}/decisions`.
- **Path IDs all validated**: `group_id`, `policy_id`, `gateway_name`,
  `target_name` go through `mcp_core.validators.validate_id`.
- **Condition operators** are static reference data → cached (TTL 300s).
- **Envelope**: lists return `{items, totalItem}`; `paging.py` handles both that
  and a `listData`/`total` fallback defensively.

## Key files

| File | Purpose |
|---|---|
| `server.py` | FastMCP entry point, CLI flags, passthrough wiring (stdio token gate + HTTP middleware), `PolicyHandler` registration |
| `config.py` | `AgentbaseConfig` (env-driven, all 6 service base URLs); no profile/creds |
| `auth.py` | `PassthroughTokenManager` guard (never mints) |
| `middleware.py` | `PassthroughIdentityMiddleware` (401 on missing bearer, seeds `user_token_var`) |
| `client.py` | `AgentbaseClient(BaseClient)` — `default_service="policy"` |
| `paging.py` | `fetch_all_agentbase_items` — 1-based paging over `{items,totalItem}` |
| `discovery_cache.py` | Identity-scoped `DiscoveryCache`; caches `list_condition_operators` only |
| `policy_handler.py` | 12 policy tools (two-tier: `_fn` logic + `PolicyHandler` delegators) |
| `models.py` | 5 `extra="forbid"` DTOs + 6 response models |
| `tool_annotations.py` | `READ`/`WRITE`/`DESTRUCTIVE` constants |

## Server flags

```bash
uv run agentbase-mcp-server                          # stdio, read-only
uv run agentbase-mcp-server --allow-write            # stdio, writes enabled
uv run agentbase-mcp-server --transport streamable-http --host 0.0.0.0 --port 8080
```

## Service porting playbook (for the next 5 services)

The pilot (`policy`) locks this pattern. To port another service:

1. **Read the ops.** Open the source
   `/Users/lap15626/.../greennode-agentbase-mcp/registry.generated.json` and
   filter `operations[]` by `"service" == "<svc>"`. Each op has `id`, `method`,
   `path`, `parameters` (path/query/header), `hasBody`, `inputSchema.body`.

2. **Name the tool** `verb_noun` with the FIRST segment in `ALLOWED_VERBS`
   (`list,get,create,update,delete,configure,upgrade,validate,apply,generate,
   manage,search`). For a non-CRUD op (no natural verb), pick a legal verb by
   semantics: e.g. `decisions` → `get_authorization_decision` (`get` returns a
   result; `evaluate`/`decide` are NOT allowed). Add `*_dryrun` for read-only
   previews (exempt from `## Requirements`).

3. **Pick the annotation** by HTTP method **and** semantic effect: GET→`READ`;
   POST/PUT/PATCH→`WRITE`; DELETE→`DESTRUCTIVE` — EXCEPT POST-but-read ops
   (`decisions`, `:search`) → `READ`. Gate `WRITE`/`DESTRUCTIVE` behind
   `allow_write`; register `READ` unconditionally.

4. **Build the request DTO** from `inputSchema.body`: camelCase fields,
   `model_config = ConfigDict(extra="forbid")`, `Literal[...]` for closed-set
   strings, `Field(ge=, le=)` for numeric bounds, `Optional[...]` for partial
   updates. Name it `*Dto`. Build the response model (`*Data`/`*Result`) as a
   plain `BaseModel` with a `from_api(cls, dict)` classmethod.

5. **Validate + URL**: `validate_id` every path id; build the path with f-string
   substitution. Body via `body.model_dump(exclude_none=True)`.

6. **Paging**: route lists through `fetch_all_agentbase_items` (`page`/`page_size`
   1-based); never expose paging params. For `limit`-based ops (e.g. some
   memory ops), add a dedicated helper rather than forcing `page` on them.

7. **Caching**: cache only static reference data (operators, versions, flavors).
   Never cache per-caller mutable resources. Expose `refresh: bool` only on
   cached tools. Scope keys via `current_identity()` (already done in
   `DiscoveryCache`).

8. **Docstrings**: `## Requirements` (and usually `## Workflow`) on every
   `create_/update_/delete_/configure_/upgrade_` async method. Keep them lean.

9. **Tests**: `respx` mock the service endpoint (NO IAM mock — passthrough);
   call `_fn(client, args)` for logic, construct `PolicyHandler` for DTO/wire
   bodies; assert `Authorization: Bearer test-bearer` is forwarded. Add
   schema-introspection + annotation tests.

10. **Satisfy the 3 CI rules**: `verb_noun` naming, `extra="forbid"` on `*Dto`,
    `## Requirements` on write methods.

When adding a service, also: change `AgentbaseClient.default_service` selection
(per-handler client is fine), add the service's tools to a new `<svc>_handler.py`,
and update this CLAUDE.md + README.

## Testing

```bash
cd src/agentbase-mcp-server && uv run pytest tests/ -v
```
Tests use `respx`; no credentials needed (passthrough — the "caller token" is a
test fixture). Verify the bearer-forwarding invariant holds in every test.
