# GreenNode MCP Server

MCP (Model Context Protocol) Server for VKS (VNG Kubernetes Service). Provides AI assistants with tools to manage Kubernetes clusters and resources on GreenNode.

## Key Features

- **Cluster Management** — Create, update, delete, and monitor VKS clusters
- **Node Group Management** — Scale, update, and manage node groups
- **Kubernetes Resources** — List pods/deployments/services, get logs, apply YAML manifests
- **Auto-Upgrade** — Configure automatic cluster version upgrades
- **Troubleshooting** — Get cluster events, pod logs, K8s events for debugging
- **Safety Controls** — Read-only by default, write operations require explicit opt-in

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Tools](#tools)
- [Security](#security)
- [Getting Help](#getting-help)
- [More Resources](#more-resources)

## Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or pip
- [GreenNode CLI](https://github.com/vngcloud/greennode-cli) (`grncli`) — **required** for credential setup
- IAM Service Account from [VNG Cloud Console](https://hcm-3.console.vngcloud.vn/iam/)

## Quickstart

### 1. Configure credentials

The MCP server supports two ways to provide credentials:

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

This creates `~/.greenode/credentials` which the MCP server reads automatically.

> **Note:** Environment variables take priority over the credentials file. The server cannot run without credentials configured via one of these methods.

### 2. Run the server

```bash
uvx vks-mcp-server
```

### 3. Configure your AI assistant

<details>
<summary><strong>Claude Desktop</strong></summary>

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "greennode.vks-mcp-server": {
      "command": "uvx",
      "args": [
        "greennode.vks-mcp-server@latest",
        "--allow-write"
      ],
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

Config file location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

</details>

<details>
<summary><strong>Claude Code</strong></summary>

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "greennode.vks-mcp-server": {
      "command": "uvx",
      "args": [
        "greennode.vks-mcp-server@latest",
        "--allow-write"
      ],
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

</details>

<details>
<summary><strong>Cursor</strong></summary>

Add to Cursor Settings → MCP Servers:

```json
{
  "mcpServers": {
    "greennode.vks-mcp-server": {
      "command": "uvx",
      "args": [
        "greennode.vks-mcp-server@latest",
        "--allow-write"
      ],
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

</details>

### Configuration options

| Field | Type | Description |
|-------|------|-------------|
| `command` | string | `"uvx"` to run from PyPI without installing |
| `args` | array | Package name with `@latest` + server flags |
| `autoApprove` | array | Tool names to auto-approve without user confirmation. Empty `[]` = ask every time |
| `disabled` | boolean | Set `true` to disable the server without removing config |

#### `autoApprove` example

Auto-approve read-only tools so AI doesn't ask confirmation for every list/get:

```json
{
  "mcpServers": {
    "greennode.vks-mcp-server": {
      "command": "uvx",
      "args": [
        "greennode.vks-mcp-server@latest",
        "--allow-write"
      ],
      "autoApprove": [
        "cluster_list",
        "cluster_get",
        "cluster_get_events",
        "nodegroup_list",
        "nodegroup_get",
        "nodegroup_list_nodes",
        "list_k8s_resources",
        "get_pod_logs",
        "get_k8s_events",
        "list_api_versions"
      ],
      "disabled": false
    }
  }
}
```

> **Tip:** Only auto-approve **read-only** tools. Keep write tools (create, update, delete) requiring manual approval for safety.

## Transport

GreenNode VKS MCP Server supports two transport modes:

| Mode | Flag | Use case |
|------|------|----------|
| stdio (default) | *(none)* | Local AI assistants — Claude Desktop, Cursor, VS Code |
| Streamable HTTP | `--transport streamable-http` | Self-hosted server, team sharing, container deployment |

> **SSE support removed:** Server Sent Events (SSE) was removed per [MCP spec 2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility). If you need SSE, use a previous version.

### Streamable HTTP (self-hosted)

Run as an HTTP server:

```bash
uvx vks-mcp-server \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8000 \
  --api-key your-secret-token
```

Configure your AI assistant to connect via HTTP:

```json
{
  "mcpServers": {
    "greennode.vks": {
      "type": "http",
      "url": "http://your-server:8000/mcp",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      }
    }
  }
}
```

**Security notes:**
- Always set `--api-key` when exposing the server on a network. Omitting it runs unauthenticated.
- `--api-key` can also be set via the `GRN_MCP_API_KEY` environment variable (recommended for production).
- For TLS termination, put a reverse proxy (nginx, Caddy) in front of the server.

### Remote hosted (planned)

A `grn-mcp-proxy` tool is planned for when GreenNode hosts a central MCP server. It will run locally, handle IAM authentication, and forward requests — similar to AWS's `mcp-proxy-for-aws` pattern.

## Configuration

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--allow-write` | `false` | Enable create, update, and delete operations. Without this flag, only read operations are available |
| `--allow-sensitive-data-access` | `false` | Enable reading Kubernetes Secrets. Without this flag, Secret resources are hidden |

> **Security Warning:** Enabling both `--allow-write` and `--allow-sensitive-data-access` gives the AI assistant full access to your cluster resources including secrets. Use with caution.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GRN_ACCESS_KEY_ID` | Client ID (overrides credentials file) |
| `GRN_SECRET_ACCESS_KEY` | Client Secret (overrides credentials file) |
| `GRN_DEFAULT_REGION` | Default region (default: HCM-3) |
| `GRN_PROFILE` | Profile name from config file (default: "default") |

Credential resolution order: environment variables take priority over the credentials file.

### Credential Files

Created by `grn configure` (shared with [GreenNode CLI](https://github.com/vngcloud/greenode-cli)). Do not edit manually:

```ini
# ~/.greenode/credentials
[default]
client_id = your-client-id
client_secret = your-client-secret
```

```ini
# ~/.greenode/config
[default]
region = HCM-3
```

### Available Regions

| Region | VKS Endpoint |
|--------|-------------|
| `HCM-3` | `https://vks.api.vngcloud.vn` |
| `HAN` | `https://vks-han-1.api.vngcloud.vn` |

## Tools

The following tools are provided by the VKS MCP server for managing VKS clusters and Kubernetes resources. Each tool performs a specific action that can be invoked by AI assistants.

### Cluster Management

#### `cluster_list`

Lists all VKS clusters in the configured region. Returns a markdown table with cluster name, ID, status, version, node count, and creation date.

Features:

* Supports pagination for large cluster lists.
* Returns formatted markdown table for AI readability.

Parameters:

* page (optional), pageSize (optional, default: 50), region (optional)

#### `cluster_get`

Gets full detail of a specific VKS cluster by ID. Returns a markdown key-value table with all cluster properties.

Features:

* Returns comprehensive cluster details including name, status, version, network config, node count.
* Input validation on cluster ID to prevent path traversal.

Parameters:

* cluster_id (required), region (optional)

#### `cluster_get_events`

Gets events for a VKS cluster. Returns a markdown table of events with type, reason, message, and timestamp.

Features:

* Supports pagination for event history.
* Useful for troubleshooting cluster issues.

Parameters:

* cluster_id (required), page (optional), pageSize (optional, default: 20), region (optional)

#### `cluster_delete_dryrun`

Preview what will be deleted when deleting a cluster. Shows cluster info and all node groups that will be removed.

Features:

* Displays cluster details and all associated node groups.
* Shows warning header and instructions to confirm deletion.
* Safe to run — does not modify any resources.

Parameters:

* cluster_id (required), region (optional)

#### `cluster_create_validate`

Validates a cluster creation body without actually creating a cluster. Returns 'valid' or a list of validation errors.

Features:

* Validates cluster name format (regex: `^[a-z0-9][a-z0-9\-]{3,18}[a-z0-9]$`).
* Checks required fields: vpcId, networkType, version, releaseChannel.
* Validates network-type-specific fields (CIDR for CALICO/CILIUM_OVERLAY).
* Validates node groups: name format, required fields, diskSize (20-5000), numNodes (0-10).

Parameters:

* body (required — CreateClusterComboDto JSON)

#### `cluster_create`

Creates a new VKS cluster. **Requires `--allow-write` flag.** Use `cluster_create_validate` first to check the body.

Features:

* Creates cluster with embedded node group configuration.
* Supports poc and autoRenewal options.

Parameters:

* body (required — CreateClusterComboDto JSON), poc (optional, default: false), autoRenewal (optional, default: true), region (optional)

#### `cluster_update`

Updates an existing VKS cluster. **Requires `--allow-write` flag.**

Features:

* Supports partial updates (only send fields to change).

Parameters:

* cluster_id (required), body (required — update fields), region (optional)

#### `cluster_delete`

Deletes a VKS cluster. **IRREVERSIBLE. Requires `--allow-write` flag.** Use `cluster_delete_dryrun` first to preview.

Features:

* Permanently removes cluster and all associated resources.

Parameters:

* cluster_id (required), region (optional)

### Auto-Upgrade

#### `cluster_auto_upgrade_config`

Configures auto-upgrade schedule for a VKS cluster. **Requires `--allow-write` flag.**

Features:

* Sets specific days and time for automatic Kubernetes version upgrades.

Parameters:

* cluster_id (required), weekdays (required — e.g. ['Mon', 'Wed', 'Fri']), time (required — HH:mm format, e.g. '03:00'), region (optional)

#### `cluster_auto_upgrade_delete`

Deletes auto-upgrade configuration for a VKS cluster. **Requires `--allow-write` flag.**

Features:

* Disables automatic cluster upgrades.

Parameters:

* cluster_id (required), region (optional)

### Node Group Management

#### `nodegroup_list`

Lists all node groups in a VKS cluster. Returns a markdown table.

Features:

* Shows node group name, ID, status, node count, flavor, image.
* Includes cluster name in context.

Parameters:

* cluster_id (required), region (optional)

#### `nodegroup_get`

Gets full detail of a specific node group. Returns a markdown key-value table.

Features:

* Shows flavor, image, disk size, scaling config, labels, taints, security groups.

Parameters:

* cluster_id (required), nodegroup_id (required), region (optional)

#### `nodegroup_list_nodes`

Lists individual nodes in a node group. Returns a markdown table with node name, ID, status, IP, and creation time.

Features:

* Supports pagination for large node groups.

Parameters:

* cluster_id (required), nodegroup_id (required), page (optional), pageSize (optional, default: 50), region (optional)

#### `nodegroup_delete_dryrun`

Preview what will be deleted when deleting a node group.

Features:

* Shows node group details and node count.
* Safe to run — does not modify any resources.

Parameters:

* cluster_id (required), nodegroup_id (required), region (optional)

#### `nodegroup_create`

Creates a new node group in a VKS cluster. **Requires `--allow-write` flag.**

Features:

* Supports full node group configuration: flavor, image, disk, scaling, security groups, SSH key.

Parameters:

* cluster_id (required), body (required — CreateNodeGroupDto JSON with name, numNodes, imageId, flavorId, diskSize, diskType, enablePrivateNodes, securityGroups, sshKeyId, upgradeConfig), region (optional)

#### `nodegroup_update`

Updates a node group. **Requires `--allow-write` flag.** `imageId` is always required in body.

Features:

* Supports partial updates for numNodes, securityGroups, labels, taints, autoScaleConfig, upgradeConfig.

Parameters:

* cluster_id (required), nodegroup_id (required), body (required — must include imageId), region (optional)

#### `nodegroup_delete`

Deletes a node group. **IRREVERSIBLE. Requires `--allow-write` flag.** Use `nodegroup_delete_dryrun` first.

Features:

* Permanently removes node group and all its nodes.

Parameters:

* cluster_id (required), nodegroup_id (required), region (optional)

### Kubernetes Resource Management

#### `list_k8s_resources`

Lists Kubernetes resources of a specific kind in a VKS cluster. Use this tool instead of `kubectl get` commands.

Features:

* Supports filtering by namespace, labels, and fields.
* Returns resource summaries with name, namespace, creation time, and metadata.
* Works with any resource kind (Pod, Service, Deployment, ConfigMap, etc.).

Parameters:

* cluster_id (required), kind (required — e.g. 'Pod', 'Service'), api_version (required — e.g. 'v1', 'apps/v1'), namespace (optional), label_selector (optional), field_selector (optional), region (optional)

#### `get_pod_logs`

Gets logs from a pod in a Kubernetes cluster. Use this tool instead of `kubectl logs`. **Requires `--allow-sensitive-data-access` flag.**

Features:

* Supports filtering by container, time range, and size.
* Can retrieve previous terminated container logs for crash debugging.

Parameters:

* cluster_id (required), namespace (required), pod_name (required), container_name (optional), since_seconds (optional), tail_lines (optional, default: 100), limit_bytes (optional, default: 10240), previous (optional, default: false), region (optional)

#### `get_k8s_events`

Gets events related to a specific Kubernetes resource. Use this tool instead of `kubectl describe` or `kubectl get events`. **Requires `--allow-sensitive-data-access` flag.**

Features:

* Returns event timestamps, occurrence counts, messages, reasons, and reporting components.
* Useful for troubleshooting pod startup failures, deployment issues, and scheduling problems.

Parameters:

* cluster_id (required), kind (required — e.g. 'Pod', 'Deployment'), name (required), namespace (optional), region (optional)

#### `list_api_versions`

Lists all available API versions in the Kubernetes cluster.

Features:

* Discovers core APIs (e.g. 'v1'), API groups (e.g. 'apps/v1'), and CRD APIs.
* Helps determine the correct apiVersion for managing resources.

Parameters:

* cluster_id (required), region (optional)

#### `manage_k8s_resource`

Manages a single Kubernetes resource with CRUD operations. Use this tool instead of `kubectl create/edit/patch/delete/get`. **Requires `--allow-write` flag for mutating operations.** **Requires `--allow-sensitive-data-access` for Secret resources.**

Features:

* Supports create, replace, patch, delete, and read operations.
* Handles both namespaced and cluster-scoped resources.

Parameters:

* operation (required — create/replace/patch/delete/read), cluster_id (required), kind (required), api_version (required), name (optional), namespace (optional), body (optional — required for create/replace/patch), region (optional)

#### `apply_yaml`

Applies Kubernetes YAML manifests from a local file. Use this tool instead of `kubectl apply -f`. **Requires `--allow-write` flag.**

Features:

* Supports multi-document YAML files.
* Can create or update existing resources.
* Path must be absolute (e.g. '/home/user/manifests/app.yaml').

Parameters:

* yaml_path (required — absolute path), cluster_id (required), namespace (required), force (optional, default: true), region (optional)

## Security

### Features

- **Read-only by default** — Write operations (create/update/delete) require `--allow-write` flag
- **Sensitive data protection** — Kubernetes Secrets hidden by default, require `--allow-sensitive-data-access`
- **Credential security** — Credentials read from `~/.greenode/credentials` with `0600` file permissions
- **Input validation** — All cluster and nodegroup IDs validated (alphanumeric + hyphens only) to prevent path traversal
- **Token handling** — Access tokens stored in memory only, never written to disk or logged
- **Request timeout** — All HTTP requests have 30s timeout to prevent hanging
- **Retry with backoff** — Automatic retry with exponential backoff (1s → 2s → 4s) for transient errors (5xx, timeouts)

### Permissions

**Read-only mode** (default):

All list, get, describe, and validation tools are available without any flags.

**Write mode** (`--allow-write`):

Enables mutating operations: `cluster_create`, `cluster_update`, `cluster_delete`, `nodegroup_create`, `nodegroup_update`, `nodegroup_delete`, `cluster_auto_upgrade_config`, `cluster_auto_upgrade_delete`, `manage_k8s_resource`, `apply_yaml`.

**Sensitive data mode** (`--allow-sensitive-data-access`):

Enables reading Kubernetes Secret resources via `list_k8s_resources` and `manage_k8s_resource`.

### Best Practices

- Start with **read-only mode** to explore clusters before enabling writes
- Use `cluster_delete_dryrun` and `nodegroup_delete_dryrun` to preview deletions
- Use `cluster_create_validate` to check parameters before creating clusters
- Review AI-generated YAML carefully before using `apply_yaml`
- Use separate IAM service accounts with minimal permissions per environment

## Getting Help

- [Open an issue](https://github.com/vngcloud/greennode-mcp/issues/new/choose) — Bug reports and feature requests
- Search [existing issues](https://github.com/vngcloud/greennode-mcp/issues) before opening a new one

## More Resources

- [Development Guide](docs/DEVELOPMENT.md) — Contributing, CI/CD, release process
- [GreenNode CLI](https://github.com/vngcloud/greennode-cli) — CLI companion tool
- [MCP Protocol](https://modelcontextprotocol.io/) — Model Context Protocol specification
- [VNG Cloud Console](https://hcm-3.console.vngcloud.vn/)

## License

Apache License 2.0 — see [LICENSE](LICENSE).
