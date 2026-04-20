# Streamable HTTP Setup Guide

This guide walks through running `greenode-mcp-server` in **Streamable HTTP**
transport mode — required when the server needs to serve remote clients,
containerized agents, or anything beyond a single local Claude Code session.

For local-only, single-user setups, **stdio is simpler** — use that unless
you specifically need HTTP. See the main [README](../src/greenode-mcp-server/README.md)
for stdio quickstart.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) installed (or `uvx` via pipx)
- VNG Cloud IAM credentials (Client ID + Client Secret from the
  [IAM Portal](https://hcm-3.console.vngcloud.vn/iam/))
- `project_id` configured (via `grn configure` or `GRN_DEFAULT_PROJECT_ID` env)

## Step 1: Generate an API key

The API key protects the HTTP endpoint — every request must carry it as a
bearer token. Without it, the server runs unauthenticated (prints a warning
on stderr and accepts any caller — only safe on an isolated network).

```bash
export GRN_MCP_API_KEY=$(openssl rand -hex 32)

# Persist for next sessions
mkdir -p ~/.greenode
echo "export GRN_MCP_API_KEY=$GRN_MCP_API_KEY" >> ~/.greenode/mcp-env
chmod 600 ~/.greenode/mcp-env
# Later: `source ~/.greenode/mcp-env`
```

Use at least 32 random bytes (64 hex chars). Rotate quarterly.

## Step 2: Start the server

**Local only** (client on the same machine):

```bash
uvx greenode-mcp-server@latest \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8000 \
  --allow-write \
  --api-key "$GRN_MCP_API_KEY"
```

**Accept remote clients** (combine with TLS + firewall — see Step 7):

```bash
uvx greenode-mcp-server@latest \
  --transport streamable-http \
  --host 0.0.0.0 \
  --port 8000 \
  --allow-write \
  --api-key "$GRN_MCP_API_KEY"
```

Expected startup log:

```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

## Step 3: Verify with curl

**Reject no-auth (401 expected):**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/mcp
```

**Initialize with auth (SSE response expected):**

```bash
curl -sN -X POST http://127.0.0.1:8000/mcp \
  -H "Authorization: Bearer $GRN_MCP_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"initialize",
    "params":{
      "protocolVersion":"2024-11-05",
      "capabilities":{},
      "clientInfo":{"name":"curl-test","version":"1"}
    }
  }' | head -20
```

Response should contain `"serverInfo":{"name":"greenode-mcp-server"...}`.

## Step 4: Connect Claude Code

```bash
claude mcp remove greenode 2>/dev/null

claude mcp add greenode --transport http \
  --url http://127.0.0.1:8000/mcp \
  --header "Authorization: Bearer $GRN_MCP_API_KEY"

claude mcp list | grep greenode
# Expected: greenode: http://127.0.0.1:8000/mcp - ✓ Connected
```

Restart the Claude Code session, then in chat:

```
/mcp
search_api("cluster")
```

## Step 5: Connect from a Python agent

```bash
uv pip install mcp
```

```python
# test_agent.py
import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    url = "http://127.0.0.1:8000/mcp"
    headers = {"Authorization": f"Bearer {os.environ['GRN_MCP_API_KEY']}"}

    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"✓ {len(tools.tools)} tools available")

            result = await session.call_tool(
                "search_api",
                {"query": "cluster", "product": "vks"},
            )
            print(f"✓ search_api result:\n{result.content[0].text[:300]}")


asyncio.run(main())
```

```bash
uv run python test_agent.py
```

## Step 6: MCP Inspector (optional GUI)

```bash
npx @modelcontextprotocol/inspector
```

Browser opens at `http://localhost:6274`. In the UI:

| Field | Value |
|-------|-------|
| Transport Type | `Streamable HTTP` |
| URL | `http://127.0.0.1:8000/mcp` |
| Authentication → Bearer Token | paste `$GRN_MCP_API_KEY` |

Click **Connect** → **Tools** tab → pick a tool → fill args → **Call**.

## Step 7: Production deployment

### systemd unit

```ini
# /etc/systemd/system/greenode-mcp.service
[Unit]
Description=GreenNode MCP Server (Streamable HTTP)
After=network.target

[Service]
Type=simple
User=mcp
Environment="GRN_ACCESS_KEY_ID=your-client-id"
Environment="GRN_SECRET_ACCESS_KEY=your-client-secret"
Environment="GRN_DEFAULT_REGION=HCM-3"
Environment="GRN_DEFAULT_PROJECT_ID=pro-xxxxxxxx"
Environment="GRN_MCP_API_KEY=long-random-hex-string"
ExecStart=/usr/local/bin/uvx greenode-mcp-server@latest \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8000 \
  --allow-write
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now greenode-mcp
sudo systemctl status greenode-mcp
```

### nginx reverse proxy with TLS

```nginx
# /etc/nginx/sites-available/mcp.yourteam.com
server {
    listen 443 ssl http2;
    server_name mcp.yourteam.com;

    ssl_certificate     /etc/letsencrypt/live/mcp.yourteam.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.yourteam.com/privkey.pem;

    location /mcp {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE streaming support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
    }
}
```

Client now connects over HTTPS:

```bash
claude mcp add greenode --transport http \
  --url https://mcp.yourteam.com/mcp \
  --header "Authorization: Bearer $GRN_MCP_API_KEY"
```

### Docker

```dockerfile
FROM python:3.13-slim
RUN pip install uv
EXPOSE 8000
CMD ["uvx", "greenode-mcp-server@latest", \
     "--transport", "streamable-http", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--allow-write"]
```

```bash
docker build -t greenode-mcp-http .

docker run -d --name greenode-mcp \
  -p 127.0.0.1:8000:8000 \
  -e GRN_ACCESS_KEY_ID=... \
  -e GRN_SECRET_ACCESS_KEY=... \
  -e GRN_DEFAULT_REGION=HCM-3 \
  -e GRN_DEFAULT_PROJECT_ID=pro-xxx \
  -e GRN_MCP_API_KEY=... \
  greenode-mcp-http
```

## Security checklist

Before exposing an HTTP server outside localhost:

- [ ] `--api-key` (or `GRN_MCP_API_KEY`) is always set — do not rely on the
      unauthenticated warning fallback
- [ ] IAM credentials live in environment variables or Secret stores, never
      hard-coded in scripts or Dockerfiles
- [ ] `--host 0.0.0.0` is only used behind a reverse proxy with TLS
- [ ] TLS certificate is valid (Let's Encrypt or internal CA)
- [ ] Firewall allows inbound only from trusted networks
- [ ] API key is rotated quarterly
- [ ] Request/response bodies are NOT logged (they may contain sensitive data)

## Auth model

Three distinct authentication layers are at play:

1. **Client → MCP server** — bearer token via `Authorization` header. Server
   checks with `hmac.compare_digest` (constant-time compare).
2. **MCP server → VNG Cloud API** — IAM Client Credentials (OAuth2) from
   env vars or `~/.greenode/credentials`. Token auto-refreshes every ~30 min.
3. **Multi-user** (not supported out of the box) — the server has a single
   set of IAM credentials. Every client that knows the bearer token acts as
   the same VNG Cloud identity. For per-user isolation, run one server
   instance per user or build a proxy that maps bearer tokens to IAM creds.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `401 Unauthorized` | Missing or wrong `Authorization` header | Check header matches `Bearer <token>` exactly, no extra whitespace |
| `406 Not Acceptable` | Missing `Accept` header | Add `Accept: application/json, text/event-stream` |
| `405 Method Not Allowed` | GET on a POST-only endpoint | Use POST for JSON-RPC requests |
| `Connection refused` | Server not running, or bound to a different host | `lsof -ti:8000` to check process; use `--host 0.0.0.0` if connecting from another machine |
| Stderr warning "Server is unauthenticated" | `--api-key` not set in HTTP mode | Always pass `--api-key` or set `GRN_MCP_API_KEY` |
| Inspector reports "Connection refused" while curl works | Inspector proxy cannot resolve the host | Try swapping `127.0.0.1` ↔ `localhost` in the URL |
| SSE stream times out mid-response | Reverse proxy `proxy_read_timeout` too short | Raise to `3600s` (see nginx example above) |
| `429 Too Many Requests` from VNG Cloud | IAM rate limit hit | Back off retries; check no hot loop is calling `call_api` repeatedly |

## TL;DR — three-line quickstart

```bash
export GRN_MCP_API_KEY=$(openssl rand -hex 32)
uvx greenode-mcp-server@latest --transport streamable-http --host 127.0.0.1 --port 8000 --allow-write --api-key "$GRN_MCP_API_KEY" &
claude mcp add greenode --transport http --url http://127.0.0.1:8000/mcp --header "Authorization: Bearer $GRN_MCP_API_KEY"
```

Restart Claude Code, then `/mcp` and `search_api("cluster")`.

## See also

- [README](../src/greenode-mcp-server/README.md) — main server docs (stdio quickstart, tool reference)
- [DEVELOPMENT.md](./DEVELOPMENT.md) — dev workflow and release process
- [MCP specification — Streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
