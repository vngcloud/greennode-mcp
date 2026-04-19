# GreenNode MCP Server — Development Guide

## Developer Workflow: Feature/Bug → Release

### Phase 1: Development

```bash
# 1. Create a feature branch
git checkout main && git pull
git checkout -b feat/add-new-feature

# 2. Code + test
# Add code in src/greenode-mcp-server/greennode/greenode_mcp_server/
# Add tests in src/greenode-mcp-server/tests/
cd src/greenode-mcp-server && uv sync --all-extras && uv run python -m pytest tests/ -v

# 3. Add changelog fragment
./scripts/new-change -t feature -c core -d "Short description of the change"

# 4. Commit + push
git add .
git commit -m "feat(core): short description"
git push -u origin feat/add-new-feature
```

### Phase 2: Pull Request

```
5. Create PR on GitHub (feat/add-new-feature → main)

6. GitHub Actions auto-trigger:

   run-tests.yml (working-directory: src/greenode-mcp-server)
   ├── Python 3.10 × Ubuntu     ✅
   ├── Python 3.10 × macOS      ✅
   ├── Python 3.13 × Ubuntu     ✅
   ├── Python 3.13 × macOS      ✅
   └── MCP protocol smoke test   ✅

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

# 9. Bump version (e.g. 0.3.2 → 0.4.0)
./scripts/bump-version minor
```

The `bump-version` script automatically:
- Updates version in `src/greenode-mcp-server/pyproject.toml`
- Merges `.changes/next-release/*.json` → `.changes/0.4.0.json`
- Clears `.changes/next-release/`
- Regenerates `CHANGELOG.md`
- Commits: `release: v0.4.0`
- Creates git tag: `v0.4.0`

```bash
# 10. Push + push tags
git push && git push --tags
```

```
11. GitHub Actions auto-trigger (release.yml):

    Job 1: test (working-directory: src/greenode-mcp-server)
      uv sync + pytest                              ✅

    Job 2: build (working-directory: src/greenode-mcp-server)
      Bake docs portal URL into _build_info.py      ✅
      Verify tag v0.4.0 == pyproject.toml 0.4.0     ✅
      uv build → dist/greenode_mcp_server-0.4.0.whl ✅
      Upload artifacts                              ✅

    Job 3: github-release
      Create GitHub Release "v0.4.0"                ✅
      Upload: whl + tar.gz                          ✅

    Job 4: publish-pypi
      Publish to PyPI (requires approval)           ✅
      → uvx greenode-mcp-server@0.4.0
```

### Phase 4: Users Install

```bash
# Run directly (recommended)
uvx greenode-mcp-server@latest

# Or install from PyPI
pip install greenode-mcp-server
```

---

## Deployment

### For end users

```bash
# 1. Install GreenNode CLI and configure credentials + project_id
# Follow https://github.com/vngcloud/greennode-cli for installation
grn configure
#   → Prompts for Client ID, Client Secret, Region, Output, Project ID
#   → Writes ~/.greenode/credentials and ~/.greenode/config

# 2. Run MCP server (read-only mode)
uvx greenode-mcp-server@latest

# 3. Run with write operations enabled
uvx greenode-mcp-server@latest --allow-write

# 4. Run with Kubernetes Secrets access
uvx greenode-mcp-server@latest --allow-sensitive-data-access
```

### Configure with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "greenode": {
      "command": "uvx",
      "args": [
        "greenode-mcp-server@latest",
        "--allow-write"
      ],
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

### Configure with Claude Code

```bash
claude mcp add greenode -- uvx greenode-mcp-server@latest --allow-write
```

Or add to project `.mcp.json`:

```json
{
  "mcpServers": {
    "greenode": {
      "command": "uvx",
      "args": [
        "greenode-mcp-server@latest",
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
    "greenode": {
      "command": "uvx",
      "args": [
        "greenode-mcp-server@latest",
        "--allow-write"
      ],
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--allow-write` | `false` | Enable write operations (POST, PUT, PATCH, DELETE) |
| `--allow-sensitive-data-access` | `false` | Enable reading Kubernetes Secrets |
| `--transport` | `stdio` | `stdio` or `streamable-http` |
| `--host` | `127.0.0.1` | Bind host for HTTP transport |
| `--port` | `8000` | Bind port for HTTP transport |
| `--api-key` | — | Bearer token for HTTP endpoint (env: `GRN_MCP_API_KEY`) |
| `--refresh-specs` | `false` | Force re-download specs from registry (bypass cache) |
| `--offline` | `false` | Use cached specs only; do not contact registry |

### Environment variables

| Variable | Description |
|----------|-------------|
| `GRN_ACCESS_KEY_ID` | Client ID (overrides credentials file) |
| `GRN_SECRET_ACCESS_KEY` | Client Secret (overrides credentials file) |
| `GRN_PROFILE` | Select profile (default: `default`) |
| `GRN_DEFAULT_REGION` | Region (default: `HCM-3`) |
| `GRN_DEFAULT_PROJECT_ID` | Project UUID — auto-substituted into `{projectId}` paths |
| `GRN_MCP_API_KEY` | Bearer token when running `--transport streamable-http` |

Resolution order for each credential / config item: environment variable → `~/.greenode/credentials` (for secrets) or `~/.greenode/config` (for non-secret settings) → built-in defaults.

---

## Spec registry

Specs are fetched from VNG Cloud's public docs portal at startup, cached at `~/.greenode/mcp-specs/`, and reused on subsequent runs.

```
~/.greenode/mcp-specs/
├── _index.json        # cached product list + ETag/Last-Modified
├── vks.json
├── vserver.json
├── vlb.json
└── ...
```

- **First run**: requires network to `docs.api.vngcloud.vn`
- **TTL**: 24 hours; uses HTTP conditional GET (ETag / If-Modified-Since)
- **Refresh**: `uvx greenode-mcp-server --refresh-specs`
- **Offline**: `uvx greenode-mcp-server --offline` (after first successful run)

### Dev override

```bash
# Point the server at a local directory of *.json specs (skips the registry fetch)
GRN_MCP_SPEC_DIR=/path/to/specs uv run greenode-mcp-server
```

### Baking a different portal URL at release time

Production releases target `https://docs.api.vngcloud.vn` by default. To ship a build that targets a different portal (staging / backup), set the `DOCS_PORTAL_URL` GitHub Actions variable on the release workflow — the `Bake docs portal URL` step in `release.yml` will write it into `_build_info.py` before `uv build`.

---

## Hotfix Flow

```bash
git checkout main
# Fix bug
cd src/greenode-mcp-server && uv run python -m pytest tests/ -v
cd ../..
./scripts/new-change -t bugfix -c auth -d "Fix token refresh"
git commit -am "fix(auth): fix token refresh"
./scripts/bump-version patch    # 0.4.0 → 0.4.1
git push && git push --tags     # → release.yml triggers
```

## Manual Release (Workflow Dispatch)

```
GitHub → Actions → Release → Run workflow → Input version: "0.4.1"
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
./scripts/new-change -t feature -c core -d "Add new feature"
./scripts/new-change -t bugfix -c auth -d "Fix token refresh"
```

Change types: `feature`, `bugfix`, `enhancement`, `api-change`

## Version Bumping

```bash
./scripts/bump-version patch   # 0.4.0 → 0.4.1 (bug fixes)
./scripts/bump-version minor   # 0.4.0 → 0.5.0 (new features)
./scripts/bump-version major   # 0.4.0 → 1.0.0 (breaking changes)
```

## CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `run-tests.yml` | PR to main/develop | Test: Python 3.10+3.13 × Ubuntu+macOS, pytest + ruff + MCP protocol smoke |
| `release.yml` | Tag push `v*`, manual dispatch | Bake URL → build → GitHub Release → PyPI publish |
| `security-scan.yml` | PR to main, push to main, weekly | Bandit + CodeQL security analysis |
| `stale.yml` | Daily schedule | Auto-close stale issues (30+7 days) |

## GitHub Repo Settings

### Secrets

| Secret | Purpose |
|--------|---------|
| `PYPI_API_TOKEN` | Publish to PyPI (or use Trusted Publisher) |

### Variables

| Variable | Purpose |
|----------|---------|
| `DOCS_PORTAL_URL` | Override docs portal URL baked into release builds (default: `https://docs.api.vngcloud.vn`) |

### Environments

| Environment | Setting |
|-------------|---------|
| `release` | Required reviewer, deployment branches: main only |

### Branch Protection (main)

- Require PR before merge
- Require status checks: `test`, `bandit`, `codeql`
- Require conversation resolution
- Do not allow bypassing
