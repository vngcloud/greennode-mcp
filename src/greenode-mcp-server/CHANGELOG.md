# Changelog

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
