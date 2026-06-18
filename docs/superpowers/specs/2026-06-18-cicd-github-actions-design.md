# Design: GitHub Actions CI/CD for greennode-mcp

Date: 2026-06-18

## Context

Cloudflare's `mcp-server-cloudflare` has 3 workflows: `branches.yml` (CI on PR:
lint/format/test/build), `main.yml` (push → checks + deploy staging), and
`release.yml` (changesets → deploy production to Workers). greennode-mcp has
**no CI** today (`.github` was dropped during the monorepo restructure). This
adds CI/CD adapted to the Python/uv/ruff/pytest stack and a Docker-image deploy
target (greennode is self-hosted in VKS, not Cloudflare Workers).

Scope chosen: **CI (lint+format+test) + build image + deploy stub.**

## Goals

1. CI gate on PR and push to `main`: ruff lint + ruff format check + pytest.
2. Build job: validate the deploy artifact (Docker image) builds.
3. Deploy workflow as a **stub** (manual `workflow_dispatch`, guarded on secrets)
   that builds and pushes the image to a registry — wired but inert until VNG
   registry credentials are provided.
4. Fix the Dockerfile so it actually builds in the uv-workspace layout and runs
   the HTTP transport (prerequisite for build/deploy).

## Non-goals

- No real production deploy (needs VNG Container Registry creds + target).
- No changesets/PyPI release flow (greennode uses commitizen; release deferred).
- No change to application code behavior (only lint/format normalization).

## Deliverables

### 1. `.github/workflows/ci.yml` — CI (PR + push to main)
- Triggers: `pull_request: [main]`, `push: [main]`.
- Job `test` (ubuntu-24.04, timeout 10m):
  - `actions/checkout@v4`
  - `astral-sh/setup-uv@v6` (pin a version; enable cache)
  - `uv sync --all-packages --all-groups` (workspace root)
  - `cd src/vks-mcp-server && uv run ruff check .`
  - `cd src/vks-mcp-server && uv run ruff format --check .`
  - `cd src/vks-mcp-server && uv run pytest tests/ -q`
- Job `build` (needs: test):
  - `docker build -f src/vks-mcp-server/Dockerfile -t greennode-vks-mcp:ci .`
    (context = repo root; validates the Dockerfile builds). No push.

### 2. `.github/workflows/deploy.yml` — deploy STUB
- Trigger: `workflow_dispatch` (manual) only (so it never runs/red automatically).
- Job guarded: `if: ${{ vars.IMAGE_REGISTRY != '' }}` (inert until configured).
- Steps: checkout → docker login to `${{ vars.IMAGE_REGISTRY }}` using
  `${{ secrets.REGISTRY_USERNAME }}` / `${{ secrets.REGISTRY_PASSWORD }}` →
  `docker build` → tag `${{ vars.IMAGE_REGISTRY }}/greennode-vks-mcp:${{ github.sha }}`
  → push.
- A header comment documents the required vars/secrets (IMAGE_REGISTRY,
  REGISTRY_USERNAME, REGISTRY_PASSWORD) and that this is a placeholder pending
  VNG Container Registry (vcr.vngcloud.vn) wiring.

### 3. Dockerfile fix (`src/vks-mcp-server/Dockerfile`)
Adapt for uv-workspace + HTTP mode (build context = repo root):
- `COPY pyproject.toml uv.lock ./` + `COPY src/vks-mcp-server/pyproject.toml src/vks-mcp-server/pyproject.toml` before sync.
- `uv sync --frozen --no-dev --extra http --package greennode.vks-mcp-server`
  (installs uvicorn from the `http` extra). Two-stage: deps first, then `COPY . /app` + sync project.
- Runtime stage: `EXPOSE 8000`; `ENTRYPOINT ["vks-mcp-server"]`;
  `CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]`.
- Keep the non-root `app` user. (docker-healthcheck.sh still matches the process.)

### 4. ruff cleanup (so CI is green on first run)
Running ruff may surface pre-existing violations. The implementer must make the
repo pass `ruff check` and `ruff format --check`:
- Apply auto-fixes: `uv run ruff check --fix .` and `uv run ruff format .`.
- For violations that are noise in test code (e.g. `D` missing-docstring rules),
  add a per-file-ignore in `src/vks-mcp-server/pyproject.toml` rather than
  writing docstrings everywhere:
  ```toml
  [tool.ruff.lint.per-file-ignores]
  "tests/**" = ["D"]
  ```
- Do NOT change application logic; only formatting / import-order / docstrings /
  config ignores. Re-run pytest after to confirm 78 still pass.
- Report the scale of changes (how many files reformatted, which ignores added).

## Testing / verification

- Local (CI cannot be run here, no docker in this sandbox):
  - `cd src/vks-mcp-server && uv run ruff check .` → clean.
  - `cd src/vks-mcp-server && uv run ruff format --check .` → clean.
  - `cd src/vks-mcp-server && uv run pytest tests/ -q` → 78 passed.
  - `uv build` (hatchling wheel) as a lightweight build sanity check if docker
    is unavailable in the implementer's env; note the Docker build is unverified
    locally and will first be exercised by the CI `build` job.
- The CI/deploy YAML is validated by being well-formed; first real run happens on
  GitHub.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| ruff surfaces many violations → CI red | Auto-fix + per-file-ignore for tests; report scale; logic untouched |
| Docker build unverified locally (no docker here) | Carefully follow the uv-workspace pattern; CI `build` job is the first real test; keep changes reversible |
| Deploy workflow failing without secrets | `workflow_dispatch` only + `if: vars.IMAGE_REGISTRY != ''` guard → inert by default |
| setup-uv / action version drift | Pin action major versions |

## Notes

- Docs: add a short "CI/CD" note to README/CLAUDE (workflows + how deploy is wired).
- Deploy production / release (commitizen-based versioning, registry push on tag)
  is a future iteration once VNG registry creds + target are decided.
