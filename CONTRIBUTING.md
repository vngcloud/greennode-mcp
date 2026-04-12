# Contributing to GreenNode MCP Server

## Getting Started

```bash
git clone https://github.com/vngcloud/greennode-mcp.git
cd greennode-mcp
uv sync  # or: pip install -e ".[dev]"
uv run python -m pytest tests/ -v
```

## Development Workflow

1. Create a feature branch: `git checkout -b feat/my-feature`
2. Make changes and add tests
3. Run tests: `uv run python -m pytest tests/ -v`
4. Commit with conventional commits: `feat(cluster): add new tool`
5. Create PR to `main`

## Adding a New Tool

1. Choose the appropriate handler in `src/vks_mcp_server/`
2. Define async method with docstring (used as tool description for AI)
3. Register in handler's `__init__`: `self.mcp.tool(name="tool_name")(self.method)`
4. Add `validate_id()` for any ID args used in URL construction
5. Check `self.allow_write` for mutating operations
6. Add tests in `tests/`

See `CLAUDE.md` for detailed conventions and rules.

## Code Style

- All source code text in English
- Async/await throughout
- `from __future__ import annotations` in all files
- Follow existing handler patterns

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
