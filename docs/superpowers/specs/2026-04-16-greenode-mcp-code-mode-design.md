# GreenNode MCP — Code Mode Architecture Design

**Date:** 2026-04-16
**Status:** Approved
**Scope:** Replace `vks-mcp-server` with `greenode-mcp-server` using Dynamic API Call (Code Mode) architecture

## Context

The current `vks-mcp-server` covers 23 tools for ~28 VKS endpoints. The long-term goal is to cover **all VNG Cloud APIs** (VKS, vServer, vStorage, vLB, DNS, CDN, vNetwork, vMonitor, vDB, and more), which may reach several hundred endpoints.

At that scale, the tool-per-operation approach breaks down:
- Each tool definition costs ~200–400 tokens — 100+ tools = 20–40k tokens just for schemas
- Model accuracy degrades above ~80–100 tools (too many choices)
- Adding a new product requires writing new tools manually

Cloudflare solved the same problem with **Code Mode**: instead of one tool per endpoint, expose 2 tools (`search()` + `execute()`) that let the model discover and call any API endpoint dynamically. Token cost becomes fixed (~1k tokens) regardless of how many endpoints exist.

This design adapts that approach for Python/greenode-mcp as **Dynamic API Call mode** — the model constructs structured API call parameters (no code execution or sandbox required).

## Goals

1. Replace `vks-mcp-server` with a new `greenode-mcp-server` using Dynamic API Call architecture
2. Cover all VNG Cloud REST APIs via bundled OpenAPI specs — adding a new product = adding a spec file
3. Keep K8s tools as explicit tools (they use the Kubernetes Python client, not REST)
4. Maintain existing security model: write guard, IAM auth, no token exposure

## Architecture

```
AI Assistant (Claude / Cursor / VS Code)
    │  stdio / Streamable HTTP
    ▼
greenode-mcp-server
    │
    ├── search_api(query, product?)   → OpenAPI index (in-memory, built at startup)
    ├── call_api(method, path, ...)   → VNG Cloud REST APIs (all products)
    └── K8s tools (6 explicit tools)  → Kubernetes Python client + kubeconfig from VKS
    │
    Auth: IAM OAuth2 (TokenManager) — token injected by server, never seen by model
    Write guard: HTTP method check in call_api()
```

## Tools

| Tool | Type | Token cost | Description |
|------|------|-----------|-------------|
| `search_api` | Dynamic | ~50 tokens fixed | Search OpenAPI index for matching endpoints |
| `call_api` | Dynamic | ~80 tokens fixed | Execute any VNG Cloud REST API call |
| K8s tools (6) | Explicit | ~1.5k tokens | `list_k8s_resources`, `get_pod_logs`, `get_k8s_events`, `list_api_versions`, `manage_k8s_resource`, `apply_yaml` |

**Total token cost:** ~1.6k tokens (vs ~5–8k today, and ~20–40k at 100+ tools)

## Tool Specifications

### `search_api(query, product?)`

Searches the in-memory OpenAPI index for endpoints matching the query.

**Parameters:**
- `query` (str) — keyword search string (e.g. "create load balancer", "list clusters")
- `product` (str, optional) — filter by product slug: `vks`, `vserver`, `vlb`, `vstorage`, `vnetwork`, `dns`, `cdn`, `vmonitor`, `vdb`

**Returns:** Top N matching endpoints with method, path, summary, parameter schema, and request body schema. N defaults to 5.

**Search algorithm:** Case-insensitive keyword match across `path + summary + description`. Simple and sufficient for <500 endpoints; no vector DB required.

**Example output:**
```
POST /v2/vlb/loadbalancers — Create a new load balancer
  Body: { name (required), scheme (required), subnets[] (required), ... }
  Region: HCM-3 / HAN

GET /v2/vlb/loadbalancers — List all load balancers
  Params: page, pageSize
```

### `call_api(method, path, region?, params?, body?)`

Executes a VNG Cloud REST API call with automatic auth injection.

**Parameters:**
- `method` (str) — HTTP method: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- `path` (str) — API path from spec (e.g. `/v1/clusters`, `/v2/vlb/loadbalancers`)
- `region` (str, optional) — `HCM-3` or `HAN`, defaults to config default region
- `params` (dict, optional) — query parameters
- `body` (dict, optional) — JSON request body

**Write guard:**
- `GET`, `HEAD` → always allowed
- `POST`, `PUT`, `PATCH`, `DELETE` → blocked unless `--allow-write` flag is set

**Security:**
- Path validation: rejects `../`, absolute URLs, non-path strings
- Token injection: server fetches IAM token via TokenManager, model never sees it
- 30s request timeout (same as current)

**Response formatting (best-effort):**
| Response | Format |
|----------|--------|
| List with `items[]` | Markdown table (key columns auto-detected) |
| Single object | Markdown key-value list |
| 202 Accepted / 204 No Content | "Operation accepted" + object if present |
| 4xx / 5xx | Error message + status code |
| Arbitrary JSON | Raw JSON fallback |

## OpenAPI Spec Management

### Storage

Specs are **bundled inside the package** at `src/greenode-mcp-server/specs/`:

```
specs/
├── vks.json
├── vserver.json
├── vlb.json
├── vstorage.json
├── vnetwork.json
├── dns.json
├── cdn.json
├── vmonitor.json
├── vdb.json
└── ...
```

Bundled (not fetched at runtime) → no network dependency at startup, works offline.

### Index

At startup, `api_index.py` loads all spec files and builds an in-memory list:

```python
{
    "product": "vlb",
    "method": "POST",
    "path": "/v2/vlb/loadbalancers",
    "summary": "Create a new load balancer",
    "description": "...",
    "parameters": [...],      # query + path params
    "request_body": {...},    # body schema
    "base_url_hcm3": "https://hcm-3.api.greennode.vn/vnetwork",
    "base_url_han": "https://han-1.api.greennode.vn/vnetwork",
}
```

`base_url` per region is read from the spec's `servers[]` array.

### Resolving the full URL

`call_api()` resolves the full URL as:
```
base_url[region] + path
```

where `base_url[region]` is read from the matched spec entry's `servers[]` array. If the spec has no `servers[]`, fallback to the REGIONS dict in `config.py` (same as current `VksClient`). If the path does not exist in any spec, `call_api()` still executes the request — the API server will return an error, which is passed back to the model as-is.

## K8s Tools

The 6 Kubernetes tools are kept as **explicit FastMCP tools**, identical to the current `vks-mcp-server` implementation:

- `list_k8s_resources` — list pods, services, deployments, etc.
- `get_pod_logs` — fetch pod logs
- `get_k8s_events` — get K8s events for a resource
- `list_api_versions` — list available API groups/versions
- `manage_k8s_resource` — CRUD a single K8s resource (requires `--allow-write` for write ops, `--allow-sensitive-data-access` for Secrets)
- `apply_yaml` — apply a YAML manifest (requires `--allow-write`)

These tools use the Kubernetes Python client with kubeconfig fetched from the VKS API — not a REST API pattern that fits `call_api()`.

## Project Structure

```
greenode-mcp/
├── src/
│   └── greenode-mcp-server/          # NEW — replaces vks-mcp-server
│       ├── pyproject.toml
│       ├── uv.lock
│       ├── CHANGELOG.md
│       ├── README.md
│       ├── specs/                    # Bundled OpenAPI specs
│       │   ├── vks.json
│       │   ├── vserver.json
│       │   └── ...
│       ├── greennode/
│       │   └── greenode_mcp_server/
│       │       ├── server.py         # CLI entry point + FastMCP setup
│       │       ├── api_index.py      # Spec loader + in-memory index + search
│       │       ├── api_caller.py     # call_api tool implementation
│       │       ├── auth.py           # TokenManager (reused from vks-mcp-server)
│       │       ├── config.py         # load_config (reused, updated for new namespace)
│       │       ├── client.py         # HTTP client (reused, renamed GreenodeClient)
│       │       ├── validators.py     # validate_id (reused)
│       │       ├── k8s_handler.py    # K8s tools (reused from vks-mcp-server)
│       │       ├── k8s_apis.py       # K8s API client (reused)
│       │       └── k8s_client_cache.py  # K8s client cache (reused)
│       └── tests/
├── scripts/
├── docs/
├── CLAUDE.md
└── README.md
```

`src/vks-mcp-server/` is **deleted** as part of this migration.

## CLI Flags

Same flags as `vks-mcp-server`:

| Flag | Default | Description |
|------|---------|-------------|
| `--allow-write` | False | Enable POST/PUT/PATCH/DELETE in `call_api()` and write K8s ops |
| `--allow-sensitive-data-access` | False | Enable reading K8s Secrets |
| `--transport` | `stdio` | `stdio` or `streamable-http` |
| `--host` | `127.0.0.1` | HTTP bind host |
| `--port` | `8000` | HTTP bind port |
| `--api-key` / `GRN_MCP_API_KEY` | — | Bearer token for HTTP mode |

## Security Rules

- **Write guard**: `call_api()` blocks non-GET methods when `allow_write=False`
- **Path validation**: rejects `../`, absolute URLs, empty paths before any HTTP call
- **Token injection**: IAM token fetched by `TokenManager`, never passed to model
- **Tokens in memory only**: never written to disk or logged
- **Credentials not logged**: error messages never include tokens or secrets
- **HTTP transport auth**: `--api-key` / `GRN_MCP_API_KEY` protects Streamable HTTP endpoint
- **Token comparison**: bearer token uses `hmac.compare_digest` (constant-time)
- **Timeout**: all HTTP requests have 30s timeout

## Migration from vks-mcp-server

| Step | Action |
|------|--------|
| 1 | Create `src/greenode-mcp-server/` with VKS spec first — feature-complete replacement for `vks-mcp-server` |
| 2 | Delete `src/vks-mcp-server/` |
| 3 | Add remaining product specs (vServer, vLB, etc.) incrementally |
| 4 | Update root README, CLAUDE.md, docs |

**User config change (Claude Desktop / Cursor):**
```json
{
  "mcpServers": {
    "greennode": {
      "command": "uvx",
      "args": ["greenode-mcp-server", "--allow-write"]
    }
  }
}
```

## Out of Scope

- Vector/semantic search for `search_api()` (keyword search sufficient for <500 endpoints)
- Code execution sandbox (Dynamic API Call avoids this entirely)
- `grn mcp-proxy` (separate project, separate brainstorm)
- Centrally hosted server deployment
- Auto-fetching updated OpenAPI specs at runtime (bundled only)
