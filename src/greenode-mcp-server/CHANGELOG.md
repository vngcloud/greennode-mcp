# Changelog

## 0.4.0

### Features
* Specs are now fetched dynamically from VNG Cloud's docs portal at server start — new products become available without a server release
* Added `--refresh-specs` flag to bypass cache and force re-download
* Added `--offline` flag to start from cache only without contacting the registry
* Added `SpecProvider` abstraction so the source can be swapped later (S3, OCI, etc.) with a one-line change

### Breaking Changes
* `vks.json` is no longer bundled in the wheel. First run of v0.4.0 on a new machine requires network access to `docs.api.vngcloud.vn`. To roll back: `uvx greenode-mcp-server@0.3.2`.

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
