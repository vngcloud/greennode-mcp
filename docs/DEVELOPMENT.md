# GreenNode MCP Server — Development Guide

## Developer Workflow: Feature/Bug → Release

### Phase 1: Development

```bash
# 1. Create a feature branch
git checkout main && git pull
git checkout -b feat/add-new-tool

# 2. Code + test
# Add tool in src/vks-mcp-server/greennode/vks_mcp_server/
# Add tests in src/vks-mcp-server/tests/
cd src/vks-mcp-server && uv sync --all-extras && uv run python -m pytest tests/ -v

# 3. Add changelog fragment
./scripts/new-change -t feature -c cluster -d "Add new cluster tool"

# 4. Commit + push
git add .
git commit -m "feat(cluster): add new tool"
git push -u origin feat/add-new-tool
```

### Phase 2: Pull Request

```
5. Create PR on GitHub (feat/add-new-tool → main)

6. GitHub Actions auto-trigger:

   run-tests.yml (working-directory: src/vks-mcp-server)
   ├── Python 3.10 × Ubuntu     ✅
   ├── Python 3.10 × macOS      ✅
   ├── Python 3.13 × Ubuntu     ✅
   └── Python 3.13 × macOS      ✅

   security-scan.yml
   ├── Bandit security lint      ✅
   └── CodeQL analysis           ✅

7. Review + merge PR to main
```

### Phase 3: Release

```bash
# 8. Checkout main
git checkout main
git pull

# 9. Bump version (e.g. 0.1.0 → 0.2.0)
./scripts/bump-version minor
```

The `bump-version` script automatically:
- Updates version in `src/vks-mcp-server/pyproject.toml`
- Merges `.changes/next-release/*.json` → `.changes/0.2.0.json`
- Clears `.changes/next-release/`
- Regenerates `CHANGELOG.md`
- Commits: `release: v0.2.0`
- Creates git tag: `v0.2.0`

```bash
# 10. Push + push tags
git push && git push --tags
```

```
11. GitHub Actions auto-trigger (release.yml):

    Job 1: test (working-directory: src/vks-mcp-server)
      uv sync + pytest                              ✅

    Job 2: build (working-directory: src/vks-mcp-server)
      Verify tag v0.2.0 == pyproject.toml 0.2.0      ✅
      uv build → dist/greennode.vks_mcp_server-0.2.0.whl ✅
      Upload artifacts                                ✅

    Job 3: github-release
      Create GitHub Release "v0.2.0"                  ✅
      Upload: whl + tar.gz                            ✅

    Job 4: publish-pypi
      Publish to PyPI (requires approval)             ✅
      → pip install greennode.vks-mcp-server==0.2.0
```

### Phase 4: Users Install

```bash
# Run directly (recommended)
uvx greennode.vks-mcp-server@latest

# Or install from PyPI
pip install greennode.vks-mcp-server
```

---

## Deployment

### For end users

```bash
# 1. Install GreenNode CLI and configure credentials
pip install grncli
grn configure

# 2. Run MCP server (read-only mode)
uvx greennode.vks-mcp-server@latest

# 3. Run with write operations enabled
uvx greennode.vks-mcp-server@latest --allow-write

# 4. Run with K8s Secrets access
uvx greennode.vks-mcp-server@latest --allow-sensitive-data-access
```

### Configure with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

### Configure with Claude Code

Add to project `.mcp.json`:

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

### Configure with Cursor

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

### Environment variables

| Variable | Description |
|----------|-------------|
| `GRN_ACCESS_KEY_ID` | Client ID (overrides credentials file) |
| `GRN_SECRET_ACCESS_KEY` | Client Secret (overrides credentials file) |
| `GRN_PROFILE` | Select profile (default: "default") |
| `GRN_DEFAULT_REGION` | Override region (default: HCM-3) |

Credential resolution order: environment variables (`GRN_ACCESS_KEY_ID`, `GRN_SECRET_ACCESS_KEY`) take priority over the credentials file (`~/.greenode/credentials`).

---

## Hotfix Flow

```bash
git checkout main
# Fix bug
cd src/vks-mcp-server && uv run python -m pytest tests/ -v
cd ../..
./scripts/new-change -t bugfix -c auth -d "Fix token refresh"
git commit -am "fix(auth): fix token refresh"
./scripts/bump-version patch    # 0.2.0 → 0.2.1
git push && git push --tags     # → release.yml triggers
```

## Manual Release (Workflow Dispatch)

```
GitHub → Actions → Release → Run workflow → Input version: "0.2.1"
```

Use when:
- Release workflow failed mid-way — re-run with same version
- Need to rebuild release artifacts without bumping version

---

## Changelog Management

```bash
# Interactive
./scripts/new-change

# CLI args
./scripts/new-change -t feature -c cluster -d "Add new tool"
./scripts/new-change -t bugfix -c auth -d "Fix token refresh"
```

Change types: `feature`, `bugfix`, `enhancement`, `api-change`

## Version Bumping

```bash
./scripts/bump-version patch   # 0.1.0 → 0.1.1 (bug fixes)
./scripts/bump-version minor   # 0.1.0 → 0.2.0 (new tools)
./scripts/bump-version major   # 0.1.0 → 1.0.0 (breaking changes)
```

## CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `run-tests.yml` | PR to main/develop | Test: Python 3.10+3.13 × Ubuntu+macOS, pytest + ruff |
| `release.yml` | Tag push `v*`, manual dispatch | Build + GitHub Release + PyPI publish |
| `security-scan.yml` | PR to main, push to main, weekly | Bandit + CodeQL security analysis |
| `stale.yml` | Daily schedule | Auto-close stale issues (30+7 days) |

## GitHub Repo Settings

### Secrets

| Secret | Purpose |
|--------|---------|
| `PYPI_API_TOKEN` | Publish to PyPI (or use Trusted Publisher) |

### Environments

| Environment | Setting |
|-------------|---------|
| `release` | Required reviewer, deployment branches: main only |

### Branch Protection (main)

- Require PR before merge
- Require status checks: `test`, `bandit`, `codeql`
- Require conversation resolution
- Do not allow bypassing
