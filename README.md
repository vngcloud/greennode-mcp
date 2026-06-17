# GreenNode MCP

A monorepo of **MCP (Model Context Protocol) servers** for VNG Cloud products,
organized as a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/).
Each product is an independent project under `src/`, sharing the `greennode`
Python namespace.

## Servers

| Project | Package | Description |
|---------|---------|-------------|
| [`src/vks-mcp-server`](src/vks-mcp-server) | `greennode.vks_mcp_server` | Tools for managing VKS (VNG Kubernetes Service) clusters and Kubernetes resources |

More servers will be added as sibling projects under `src/`.

## Layout

```
greenode-mcp/
├── pyproject.toml          # uv workspace root (members = ["src/*"])
├── src/
│   └── vks-mcp-server/     # one product = one independent project
│       ├── pyproject.toml
│       ├── greennode/
│       │   └── vks_mcp_server/
│       └── tests/
└── docs/
```

## Getting started

```bash
# Install all workspace members into a shared environment
uv sync

# Run a specific server
uv run vks-mcp-server
```

See each project's own README for configuration and usage.

## Development

```bash
# Run a product's tests
cd src/vks-mcp-server && uv run pytest tests/ -v
```

Conventions for adding tools and new servers live in [CLAUDE.md](CLAUDE.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
