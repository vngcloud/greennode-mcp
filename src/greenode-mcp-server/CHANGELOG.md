# Changelog

## 0.4.1

### Fixes
* Restore loose Ingress assertion in `test_status_summary.py` — the CodeQL autofix bot had rewritten it as strict equality with a missing separator space, causing CI to fail on the v0.4.0 tag. No runtime behavior change.

## 0.4.0

### Features
* **Dynamic spec registry** — specs fetched from VNG Cloud's docs portal (`docs.api.vngcloud.vn`) at server start, cached at `~/.greenode/mcp-specs/`. New products appear automatically without a server release.
* **`--refresh-specs`** flag: bypass cache and force re-download
* **`--offline`** flag: start from cache only without contacting the registry
* **`SpecProvider` abstraction** so the source can be swapped later (S3, OCI, etc.) with a one-line change
* **`call_api` path-placeholder resolution**: `{projectId}` / `{project_id}` auto-substituted from `~/.greenode/config` (set by `grn configure`) or `GRN_DEFAULT_PROJECT_ID` env var
* **`call_api` raw mode**: pass `raw=True` to get the full JSON response instead of the default markdown table
* **`call_api` response guards**: 800 KB size cap + 100-row list limit, both with actionable error/footer directing the caller to paginate
* **Smart search**: fallback tiers (scoped AND → all-products AND → scoped OR → all-products OR), simple stemming (plural → singular), synonyms (e.g. `vpc` → `network`), relevance ranking (summary > path > description)
* **`list_k8s_resources`** returns a `status_summary` field per item (e.g. `"Running (ready 1/1, restarts 0)"`, `"3/3 ready"`, `"Bound (10Gi)"`) so a single list call is enough to see health without per-item reads
* **`list_k8s_resources` / `manage_k8s_resource`**: `api_version` is optional for common built-in kinds (Pod, Deployment, PVC, Ingress, Job, ...) via a built-in defaults map
* **`apply_yaml`** now accepts inline `yaml_content` in addition to file `yaml_path`; `namespace` is optional
* **Response formatter**: recognizes multiple list wrapper keys (`items`, `listData`, `data`, `results`, `records`), single-field objects render as plain `key: value`

### Fixes
* **Kubeconfig parsing**: VKS `/v1/clusters/{id}/kubeconfig` returns a JSON wrapper (`{"kubeConfig": "<yaml>", "status": "ACTIVE", ...}`) — we now extract the `kubeConfig` field and check `status` instead of treating the whole body as YAML
* **Pod logs / K8s events** no longer require `--allow-sensitive-data-access`; only reading K8s **Secrets** requires it
* **LocalDirProvider** (dev/test) bypasses the production cache — running with `GRN_MCP_SPEC_DIR` no longer pollutes `~/.greenode/mcp-specs/`

### Breaking Changes
* `vks.json` is no longer bundled in the wheel. First run of v0.4.0 on a new machine requires network access to `docs.api.vngcloud.vn`. To roll back: `uvx greenode-mcp-server@0.3.2`.
* `VksConfig` renamed to `GreenodeConfig` (also `VksClient` → `GreenodeClient`). External callers using these types need to update imports.
* Non-default profiles are now read from the `[profile <name>]` config section (AWS convention, matches `greenode-cli`). Existing configs written under `[<name>]` won't be picked up — re-run `grn configure --profile <name>`.

## 0.3.2

### Fixes
* `search_api` now matches product name (e.g. query "vks" returns VKS endpoints)

## 0.3.1

### Fixes
* Add README.md, LICENSE, and NOTICE to package (fixes missing PyPI description)

## 0.3.0

### Features
* Replace `vks-mcp-server` with `greenode-mcp-server` using Dynamic API Call (Code Mode) architecture
* `search_api` — keyword search over bundled OpenAPI specs to discover API endpoints
* `call_api` — execute any VNG Cloud REST API with automatic IAM auth injection
* 6 K8s tools retained as explicit tools (list resources, pod logs, events, apply YAML, etc.)
* Bundle VKS OpenAPI spec (28 endpoints)
* Streamable HTTP transport with bearer token authentication
* Write guard: POST/PUT/PATCH/DELETE blocked unless `--allow-write` is set
