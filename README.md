# GreenNode MCP Servers

MCP (Model Context Protocol) Servers for GreenNode services. Provides AI assistants with tools to manage GreenNode infrastructure from natural language.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) lets AI assistants (Claude, Cursor, Gemini, etc.) interact with external tools and data sources. MCP servers expose tools that AI can call to perform actions on your behalf.

This repo ships one server — **[GreenNode MCP Server](src/greenode-mcp-server/)** — which covers all VNG Cloud products (VKS, vServer, vLB, vStorage, vNetwork, DNS, CDN, vMonitor, vDB, ...) via a dynamic spec registry, plus Kubernetes resource management tools. New products appear automatically when they're added to the VNG Cloud docs portal — no server release needed.

## Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- GreenNode credentials — via environment variables or credentials file

### Credential setup

**Option A: Environment variables**

```bash
export GRN_ACCESS_KEY_ID=your-client-id
export GRN_SECRET_ACCESS_KEY=your-client-secret
export GRN_DEFAULT_REGION=HCM-3
export GRN_DEFAULT_PROJECT_ID=pro-xxxxxxxx   # required for many APIs that embed project in the URL
```

**Option B: GreenNode CLI (recommended)**

```bash
grn configure
```

The wizard auto-detects your `project_id` and writes:

- `~/.greenode/credentials` — `client_id`, `client_secret`
- `~/.greenode/config` — `region`, `project_id`, `output`

See [greenode-cli](https://github.com/vngcloud/greennode-cli).

Environment variables take priority over the files. All MCP servers in this repo read these same paths and env vars.

## Quick Start

GreenNode MCP Server supports two transport modes. Pick based on where your AI client runs:

| Mode | Use when | Setup effort |
|------|----------|--------------|
| **stdio** | Client on the same machine (Claude Code/Desktop, Cursor local) | Zero — one line |
| **Streamable HTTP — local** | Testing HTTP, or client is a local Python agent / MCP Inspector | One command |
| **Streamable HTTP — remote** | Team share, remote agents, deploy to server / container | Full runbook ([docs/STREAMABLE-HTTP.md](docs/STREAMABLE-HTTP.md)) |

### Mode 1 — stdio (local, default)

**Claude Code:**

```bash
claude mcp add greenode -- uvx greenode-mcp-server --allow-write
```

**Claude Desktop** — edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

**Cursor** — Settings → MCP Servers → paste the same JSON.

**Other MCP clients** — configure `uvx greenode-mcp-server --allow-write` as the stdio command.

### Mode 2 — Streamable HTTP (local)

Run the server as an HTTP endpoint on your own machine. Useful for testing the HTTP surface, MCP Inspector, or local Python agents.

```bash
# Terminal 1 — start the server
export GRN_MCP_API_KEY=$(openssl rand -hex 32)
uvx greenode-mcp-server \
  --transport streamable-http \
  --host 127.0.0.1 --port 8000 \
  --allow-write \
  --api-key "$GRN_MCP_API_KEY"

# Terminal 2 — connect Claude Code to it
claude mcp add greenode --transport http \
  --url http://127.0.0.1:8000/mcp \
  --header "Authorization: Bearer $GRN_MCP_API_KEY"
```

Smoke test with curl:

```bash
curl -sN -X POST http://127.0.0.1:8000/mcp \
  -H "Authorization: Bearer $GRN_MCP_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | head -5
```

Or from a Python agent:

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

### Mode 3 — Streamable HTTP (remote, team-shared)

Run on a VM/container behind nginx + TLS; team members connect over HTTPS.

**TL;DR on the server:**

```bash
# 1. Install Docker + nginx + certbot on an Ubuntu VM
# 2. Put credentials in /opt/greenode-mcp/.env (chmod 600)
# 3. docker compose up -d   (see docs/STREAMABLE-HTTP.md for compose file)
# 4. nginx + certbot --nginx -d mcp.yourteam.com
```

**Team members connect:**

```bash
# API key shared via vault (1Password, Vault, etc.) — never Slack plaintext
claude mcp add greenode --transport http \
  --url https://mcp.yourteam.com/mcp \
  --header "Authorization: Bearer $GRN_MCP_API_KEY"
```

Full runbook (VM provisioning, DNS, nginx config, TLS, firewall, monitoring, key rotation): **[docs/STREAMABLE-HTTP.md](docs/STREAMABLE-HTTP.md)**.

### Verify connected

Inside Claude Code:

```
/mcp                       → should show greenode ✓ Connected
search_api("cluster")      → should return VKS endpoints
```

## Repository Structure

```
greenode-mcp/
├── src/
│   └── greenode-mcp-server/            # GreenNode MCP Server
│       ├── README.md                    # Server-specific docs, tools, security
│       ├── pyproject.toml               # Package config + dependencies
│       ├── greennode/
│       │   └── greenode_mcp_server/     # Source code (incl. registry/ module)
│       └── tests/                       # Test suite
├── scripts/                             # Release scripts
├── docs/                                # Development guide
├── CLAUDE.md                            # AI assistant conventions
└── pyproject.toml                       # Root tool config
```

## Security

Detailed security rules in [server README](src/greenode-mcp-server/README.md#security). At a glance:

- **Read-only by default** — write ops require `--allow-write`
- **Sensitive data** — Kubernetes Secrets require `--allow-sensitive-data-access`
- **Credentials** — file permissions `0600`, never logged or written beyond `~/.greenode/`
- **Transport** — `stdio` and `streamable-http` only; SSE is removed per [MCP spec 2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)

## Getting Help

- [Open an issue](https://github.com/vngcloud/greenode-mcp/issues/new/choose) — Bug reports and feature requests
- Search [existing issues](https://github.com/vngcloud/greenode-mcp/issues) before opening a new one

## More Resources

- [GreenNode MCP Server](src/greenode-mcp-server/) — Tools, configuration, and security details
- [Development Guide](docs/DEVELOPMENT.md) — Contributing, CI/CD, release process
- [GreenNode CLI](https://github.com/vngcloud/greenode-cli) — CLI companion tool
- [MCP Protocol](https://modelcontextprotocol.io/) — Model Context Protocol specification
- [VNG Cloud Console](https://hcm-3.console.vngcloud.vn/)

## License

Apache License 2.0 — see [LICENSE](LICENSE).
