# GreenNode MCP Server

MCP (Model Context Protocol) Server for VNG Cloud. Provides AI assistants with tools to manage all VNG Cloud services from natural language.

## Key Features

- **Dynamic API Call** — Two tools (`search_api` + `call_api`) cover all VNG Cloud REST APIs
- **Live spec registry** — Specs fetched from VNG Cloud's docs portal at startup; new products appear automatically without a server release
- **Kubernetes Resources** — List pods/deployments/services, get logs, apply YAML manifests
- **Safety Controls** — Read-only by default, write operations require explicit opt-in
- **Streamable HTTP** — Remote hosting via `--transport streamable-http`

## Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or pip
- GreenNode credentials — via environment variables or credentials file

### Credential setup

**Option A: Environment variables**

```bash
export GRN_ACCESS_KEY_ID=your-client-id
export GRN_SECRET_ACCESS_KEY=your-client-secret
export GRN_DEFAULT_REGION=HCM-3
export GRN_DEFAULT_PROJECT_ID=pro-xxxxxxxx   # substituted into {projectId} paths
```

**Option B: GreenNode CLI (recommended)**

```bash
grn configure
```

The wizard auto-detects and saves your `project_id` alongside credentials:

- `~/.greenode/credentials` — `client_id`, `client_secret`
- `~/.greenode/config` — `region`, `project_id`, `output`

See [greenode-cli](https://github.com/vngcloud/greennode-cli) for install instructions.

### Profiles

Both the credentials and config files support profile sections. Select one via `GRN_PROFILE=<name>`. Each profile gets its own region and `project_id`, so switching profile switches every identity detail in one move.

## Quickstart

Pick a transport mode based on where your client runs:

| Mode | Use case | Section |
|------|----------|---------|
| **stdio** (default) | Client on the same machine (Claude Code/Desktop, Cursor local) | [Mode 1](#mode-1--stdio-local) |
| **Streamable HTTP — local** | Testing HTTP surface, local Python agents, MCP Inspector | [Mode 2](#mode-2--streamable-http-local) |
| **Streamable HTTP — remote** | Team share, remote agents, server deployment | [Mode 3](#mode-3--streamable-http-remote) |

### Mode 1 — stdio (local)

**Claude Code:**

```bash
claude mcp add greenode -- uvx greenode-mcp-server --allow-write
```

**Claude Desktop / Cursor** — add to the client's MCP config:

```json
{
  "mcpServers": {
    "greenode": {
      "command": "uvx",
      "args": ["greenode-mcp-server", "--allow-write"]
    }
  }
}
```

Client spawns `uvx greenode-mcp-server` as a subprocess, communicates via stdin/stdout JSON-RPC.

### Mode 2 — Streamable HTTP (local)

Run the server as an HTTP endpoint on your own machine.

```bash
# Generate an API key and start the server
export GRN_MCP_API_KEY=$(openssl rand -hex 32)
uvx greenode-mcp-server \
  --transport streamable-http \
  --host 127.0.0.1 --port 8000 \
  --allow-write \
  --api-key "$GRN_MCP_API_KEY"

# In another terminal, connect Claude Code
claude mcp add greenode --transport http \
  --url http://127.0.0.1:8000/mcp \
  --header "Authorization: Bearer $GRN_MCP_API_KEY"
```

Quick smoke test:

```bash
curl -sN -X POST http://127.0.0.1:8000/mcp \
  -H "Authorization: Bearer $GRN_MCP_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | head -5
```

Python agent (MCP SDK):

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client(
    "http://127.0.0.1:8000/mcp",
    headers={"Authorization": f"Bearer {api_key}"},
) as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
```

### Mode 3 — Streamable HTTP (remote)

Deploy behind nginx + TLS for team access. Full runbook:
**[docs/STREAMABLE-HTTP.md](../../docs/STREAMABLE-HTTP.md)** covers VM provisioning, Docker deployment, TLS, firewall, monitoring, and key rotation.

TL;DR — after server is deployed at `https://mcp.yourteam.com`:

```bash
claude mcp add greenode --transport http \
  --url https://mcp.yourteam.com/mcp \
  --header "Authorization: Bearer $GRN_MCP_API_KEY"
```

### Verify

In any client:

```
/mcp                         → greenode ✓ Connected
search_api("cluster")        → returns VKS endpoints
```

## Tools

### `search_api`

Search VNG Cloud API endpoints by keyword. Use this to discover which endpoint to call.

```
search_api(query="create cluster")
search_api(query="list load balancers", product="vlb")
```

### `call_api`

Execute any VNG Cloud REST API call. IAM auth token is injected automatically.

```
call_api(method="GET", path="/v1/clusters")
call_api(method="POST", path="/v1/clusters", body={"name": "my-cluster", ...})
```

**Path placeholders:** Leave `{projectId}` / `{project_id}` in the path — the server
substitutes your project UUID from `~/.greenode/config` (set by `grn configure`) or
`GRN_DEFAULT_PROJECT_ID`.

```
call_api(method="GET", path="/v2/{projectId}/networks", product="vserver")
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `method` | `str` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `path` | `str` | API path, e.g. `/v1/clusters` |
| `product` | `str?` | `vks`, `vlb`, `vserver`, ... (helps resolve the base URL) |
| `region` | `str?` | `HCM-3` or `HAN` (default: from config) |
| `params` | `dict?` | Query params (pagination is 1-based: `page=1` is first page) |
| `body` | `dict?` | JSON body for POST/PUT/PATCH |
| `raw` | `bool` | `True` returns full JSON; default formats list → markdown table (first 6 columns, top 100 rows) |

Response size is capped at 800 KB — if the API returns more, `call_api` asks you to paginate.

### Kubernetes Resource Management

Requires kubeconfig from VKS API.

| Tool | Description |
|------|-------------|
| `list_k8s_resources` | List K8s resources (Pods, Services, Deployments, etc.) |
| `get_pod_logs` | View pod logs |
| `get_k8s_events` | View resource events |
| `list_api_versions` | List available API versions |
| `manage_k8s_resource` | CRUD single K8s resource |
| `apply_yaml` | Apply YAML manifest |

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--allow-write` | `false` | Enable write operations (POST, PUT, PATCH, DELETE) |
| `--allow-sensitive-data-access` | `false` | Enable reading K8s Secrets |
| `--transport` | `stdio` | `stdio` or `streamable-http` |
| `--host` | `127.0.0.1` | Bind host for HTTP transport |
| `--port` | `8000` | Bind port for HTTP transport |
| `--api-key` | — | Bearer token for HTTP endpoint (env: `GRN_MCP_API_KEY`) |
| `--refresh-specs` | — | Bypass cached specs; force re-download from registry |
| `--offline` | — | Skip registry fetch; use cached specs only |

## Spec Registry

Specs are fetched from VNG Cloud's public docs portal at server start and cached locally at `~/.greenode/mcp-specs/`.

- **First run** requires internet access to `docs.api.vngcloud.vn`
- **Subsequent runs** reuse the cache; refresh is automatic once per 24 hours (or on `--refresh-specs`)
- **Offline mode** (`--offline`) works once the cache has been populated by at least one successful run

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Cannot reach spec source` on first run | No network to `docs.api.vngcloud.vn` | Restore network; or populate cache offline from another machine |
| `search_api` returns empty for a known product | Product's docs page changed format | Run with `--refresh-specs` to re-fetch; report if persists |
| Stale spec despite product update | Cache TTL has not expired (24 h) | Run with `--refresh-specs` to force re-download |

## Security

- **Read-only by default** — Write operations require `--allow-write`
- **Sensitive data protection** — K8s Secrets require `--allow-sensitive-data-access`
- **Path validation** — Rejects `../` and non-path strings before any HTTP call
- **Token injection** — IAM token managed by server, never exposed to AI model
- **Tokens in memory only** — Never written to disk or logged
- **HTTP auth** — Streamable HTTP protected via `--api-key` with constant-time comparison
- **Request timeout** — 30s for all HTTP requests

## License

Apache License 2.0 — see [LICENSE](LICENSE).
