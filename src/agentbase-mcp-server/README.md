# GreenNode Agentbase MCP Server

MCP server for the Agentbase **policy** service (pilot — other Agentbase
services will follow). Runs **passthrough-only**: the server holds no
service-account credentials — every upstream call forwards the caller's IAM
bearer token.

> The pilot ports the `policy` service (12 tools) to lock the pattern for the
> other five Agentbase services (runtime, identity, memory, gateway, cr).

## Tools — Policy (12)

### Reference
| Tool | Access | Description |
|---|---|---|
| `list_condition_operators` | read (cached) | List supported condition operators (`refresh: true` bypasses the cache). |

### Policy groups
| Tool | Access | Description |
|---|---|---|
| `list_policy_groups` | read | List policy groups (optional `name` filter). |
| `get_policy_group` | read | Get a policy group by id. |
| `create_policy_group` | **write** | Create a policy group (`--allow-write`). |
| `update_policy_group` | **write** | Partial-update a policy group. |
| `delete_policy_group` | destructive | Delete a policy group (`--allow-write`). |

### Policies
| Tool | Access | Description |
|---|---|---|
| `list_policies` | read | List policies in a group (optional `name` filter). |
| `get_policy` | read | Get a policy by id. |
| `create_policy` | **write** | Create a policy in a group. |
| `update_policy` | **write** | Partial-update a policy. |
| `delete_policy` | destructive | Delete a policy (`--allow-write`). |

### Decisions
| Tool | Access | Description |
|---|---|---|
| `get_authorization_decision` | read | Evaluate an authorization request — returns allow/deny. POST-but-read (no `--allow-write` needed). |

## Setup (passthrough)

stdio — set the caller token in the environment:
```bash
export GREENNODE_MCP_TOKEN="<iam-bearer-token>"
uv run agentbase-mcp-server            # read-only (default)
uv run agentbase-mcp-server --allow-write
```
Missing token on stdio exits non-zero.

HTTP — pass the bearer per request; missing → 401:
```bash
uv run agentbase-mcp-server --transport streamable-http --host 0.0.0.0 --port 8080
```
Each request: `Authorization: Bearer <iam-bearer-token>`.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `GREENNODE_MCP_TOKEN` | — | Caller IAM bearer token (stdio). |
| `TOKEN_ENV` | `GREENNODE_MCP_TOKEN` | Name of the env var holding the stdio token. |
| `AGENTBASE_DEFAULT_REGION` | `prod` | Region label (single prod region). |
| `AGENTBASE_<SERVICE>_BASE_URL` | prod const | Override one service's base URL (e.g. `AGENTBASE_POLICY_BASE_URL`). |

## Testing

```bash
cd src/agentbase-mcp-server && uv run pytest tests/ -v
```
Tests use `respx` to mock all HTTP; no credentials needed.
