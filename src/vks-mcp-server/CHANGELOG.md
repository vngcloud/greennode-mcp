# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.1.0

### Added

- Initial release of VKS MCP Server with 27 tools
- Cluster management (list, get, create, update, delete, kubeconfig, events)
- Node group management (list, get, create, update, delete, nodes, dry-run)
- Auto-upgrade configuration
- Kubernetes resource management (list, manage, apply YAML, logs, events)
- Version and image listing
- OAuth2 Client Credentials authentication with auto-refresh
- Retry with exponential backoff for transient errors
- Input validation for resource IDs
- Environment variable and profile support
