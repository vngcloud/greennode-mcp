# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

- `nodegroup_images_list` tool (and its `/v1/node-group-images` helper).

### Changed

- Reorganized as an independent project under `src/vks-mcp-server/` within the
  GreenNode MCP monorepo (uv workspace). The import package is now
  `greennode.vks_mcp_server`.

### Added

- Self-documenting tool schemas: `Literal` enums and numeric `Field(ge=, le=)`
  constraints, enriched `body` parameter descriptions, and structured docstrings
  across the cluster, nodegroup, version, and k8s tools.
- `generate_app_manifest` tool: scaffolds a Deployment + LoadBalancer Service manifest (VKS `vks.vngcloud.vn/scheme` annotation) and writes it for `apply_yaml`.
- `nodegroup_upgrade_version` tool: upgrade a node group's Kubernetes version (POST .../node-groups/{id}/upgrade-version).
- `cluster_auto_healing_config` tool: configure cluster auto-healing (PATCH /v1/clusters/{id}/auto-healing-config).

## [0.1.0]

### Added

- Initial VKS MCP server: 27 tools across Auth, Cluster, NodeGroup, Version, and
  Kubernetes handlers. Read-only by default; write and sensitive-data access are
  opt-in via `--allow-write` and `--allow-sensitive-data-access`.
