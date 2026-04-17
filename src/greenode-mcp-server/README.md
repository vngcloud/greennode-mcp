# GreenNode MCP Server

MCP (Model Context Protocol) Server for VNG Cloud. Provides AI assistants with tools to manage all VNG Cloud services from natural language.

## Key Features

- **Dynamic API Call** — Two tools (`search_api` + `call_api`) cover all VNG Cloud REST APIs
- **OpenAPI-driven** — Adding a new product = adding a spec file to `specs/`
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
```

**Option B: Credentials file (via GreenNode CLI)**

```bash
pip install grncli
grn configure
```

This creates `~/.greenode/credentials` which the server reads automatically.

## Quickstart

```bash
uvx greenode-mcp-server
```

### Claude Desktop / Cursor configuration

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

## Supported Products

Products are added by bundling OpenAPI specs in `specs/`. Currently available:

| Product | Spec file | Endpoints |
|---------|-----------|-----------|
| VKS (VNG Kubernetes Service) | `vks.json` | 28 |

More products (vServer, vLB, vStorage, vNetwork, DNS, CDN, vMonitor, vDB) will be added incrementally.

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
