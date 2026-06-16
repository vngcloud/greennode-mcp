# Design: Description & Schema Upgrade for greennode-mcp

Date: 2026-06-16

## Context

greennode-mcp exposes 27 tools across 5 handlers (auth, cluster, nodegroup,
version, k8s) built on FastMCP. Tool descriptions and parameter schemas are the
API the LLM reads to decide which tool to call and what arguments to pass. This
upgrade improves description/schema quality across all tools, following the
conventions used by the AWS Labs MCP servers and Cloudflare's MCP monorepo.

A prior analysis considered adding explicit `CallToolResult(isError=True)` for
error branches (AWS style). This was **dropped**: FastMCP (mcp 1.27.0) already
wraps raised exceptions into `isError=True` results, and greennode already
raises clean messages (`client._raise_error` → "Resource not found: ...";
`validate_id` → "Invalid cluster_id: ..."). greennode's write-guard is
"don't register the tool when read-only", so there is no "not allowed" branch
that needs a manual error result. Manual `isError` would be redundant.

## Goals

- Improve descriptions and schemas for all 27 tools so the LLM selects and calls
  tools more accurately.

## Non-goals

- No manual `CallToolResult(isError=True)` (FastMCP already handles it).
- No conversion of `body: dict` parameters to Pydantic models.
- No changes to execution logic, transport (stays stdio), or auth.

## Key finding shaping scope

`k8s_handler.py` (6 tools) already meets the target standard: structured
docstrings (`## Requirements`, `## Usage Tips`), "IMPORTANT: Use this tool
instead of kubectl ...", and `json.dumps(model.model_dump())` returns. It needs
only the `operation` Literal change. The real work is the other 4 handlers
(cluster, nodegroup, version, auth), which currently use one-line docstrings.

## Confirmed enum values (sourced from code / shared greennode-cli)

- `networkType`: `CALICO`, `CILIUM_OVERLAY`, `CILIUM_NATIVE_ROUTING`
  (greennode-cli `create_cluster.go`, `completion.go`)
- `releaseChannel`: `RAPID`, `STABLE` (default `STABLE`)
- k8s `operation`: `create`, `replace`, `patch`, `delete`, `read`
  (`models.py` `Operation` enum)
- `diskType`: CLI exposes `--disk-type` but does NOT enumerate values →
  description only, NOT a `Literal`.

Numeric constraints (from `validators` / handler logic):
- `diskSize`: 20–5000, `numNodes`: 0–10 (both live inside `body: dict`)

## Changes by group

### Group A — `Literal` for finite-value direct parameters
- `manage_k8s_resource.operation`: `str` → `Literal["create","replace","patch","delete","read"]`.
  This is the only enum that sits as a direct tool parameter (others live inside
  `body: dict`, where Literal cannot apply).

### Group B — `Field(ge=, le=)` for numeric direct parameters
- `get_pod_logs`: `tail_lines` (ge=1), `limit_bytes` (ge=1), `since_seconds` (ge=0).
- `cluster_list`, `cluster_get_events`, `nodegroup_list_nodes`: `page` (ge=0),
  `pageSize` (ge=1).
- `diskSize`/`numNodes` stay inside `body: dict` → cannot be schema-constrained;
  remain validated in `cluster_create_validate` and documented in the body
  description.

### Group C — enrich `body` descriptions
For `cluster_create`, `cluster_update`, `nodegroup_create`, `nodegroup_update`:
list required fields, valid values (`releaseChannel`: RAPID|STABLE; `networkType`:
CALICO|CILIUM_OVERLAY|CILIUM_NATIVE_ROUTING), conditional logic
(CALICO/CILIUM_OVERLAY require `cidr`; CILIUM_NATIVE_ROUTING requires
`secondarySubnets`), numeric ranges (diskSize 20–5000, numNodes 0–10).

### Group D — structured docstrings for the 4 lagging handlers
Add `## Requirements` / `## Workflow` sections and "use this tool instead of
greenode-cli/kubectl" guidance to create/update/delete tools, mirroring the
existing k8s_handler style. State workflow order, e.g.
`cluster_versions_list` → `cluster_create_validate` → `cluster_create`.

## Testing

- Re-run the existing 44 tests — must stay green (description/schema changes do
  not alter the success path).
- Risk: adding `Literal` / `Field(ge,le)` makes FastMCP validate more strictly.
  A test passing an invalid `operation` or a negative number may shift from an
  internal `RuntimeError` to a FastMCP validation error. Inspect and update such
  tests if found — this is an intentional tightening.
- Update docs per CLAUDE.md "Documentation update rule" (README / CLAUDE /
  changelog) if the tool list or descriptions change materially.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Inventing wrong enum values | Only use `Literal` for values confirmed in code/CLI; `diskType` is description-only |
| `Literal` breaks existing tests | Run tests, update if needed; intentional validation tightening |
| Over-long `body` descriptions | Keep concise — prioritize required fields + conditional logic |

## Out of scope / future

- Switching transport to Streamable HTTP + OAuth for multi-user (analyzed
  separately; stays stdio for now).
- Packaging entry point + `dependencies=` for `uvx` install.
- Replacing `body: dict` with Pydantic models for full nested schema.
