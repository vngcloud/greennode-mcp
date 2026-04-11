# Greenode CLI — Development Guide

## Developer Workflow: Feature/Bug → Release

### Phase 1: Development

```bash
# 1. Create a new branch
git checkout -b feat/add-vks-describe-events

# 2. Code + test
vim grncli/customizations/vks/describe_events.py
python -m pytest tests/ -v

# 3. Add changelog fragment
./scripts/new-change -t feature -c vks -d "Add describe-events command"
# → Creates: .changes/next-release/feature-vks-a1b2c3d4.json

# 4. Commit + push
git add .
git commit -m "feat(vks): add describe-events command"
git push -u origin feat/add-vks-describe-events
```

### Phase 2: PR to develop (testing)

```
5. Create PR on GitHub (feat/add-vks-describe-events → develop)

6. GitHub Actions auto-trigger:

   run-tests.yml
   ├── Python 3.10 × Ubuntu     ✅
   ├── Python 3.10 × macOS      ✅
   ├── Python 3.10 × Windows    ✅
   ├── Python 3.11 × Ubuntu     ✅
   ├── ...
   └── Python 3.13 × Windows    ✅

   bundle-test.yml
   ├── Python 3.10 × Ubuntu     ✅
   ├── Python 3.10 × macOS      ✅
   ├── Python 3.13 × Ubuntu     ✅
   └── Python 3.13 × macOS      ✅

7. Review + merge PR to develop
8. Test on develop environment
```

### Phase 3: PR to main (release-ready)

```
9. Create PR on GitHub (feat/add-vks-describe-events → main)
   - Same CI checks run again on main
   - Review + merge PR to main
```

### Phase 4: Release

```bash
# 10. Checkout main
git checkout main
git pull

# 11. Bump version (e.g. 0.1.0 → 0.2.0)
./scripts/bump-version minor
```

The `bump-version` script automatically:
- Updates `grncli/__init__.py`: `'0.1.0'` → `'0.2.0'`
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

    Job 1: test
      pip install + pytest                          ✅

    Job 2: build (depends on test)
      Verify tag v0.2.0 == __init__.py 0.2.0        ✅
      python -m build → dist/grncli-0.2.0.whl       ✅
      scripts/make-bundle → grncli-bundle.zip        ✅
      Upload artifacts                               ✅

    Job 3: github-release (depends on build)
      Create GitHub Release "v0.2.0"                 ✅
      Upload: grncli-0.2.0.whl
              grncli-0.2.0.tar.gz
              grncli-bundle.zip

    Job 4: publish-pypi (depends on build)
      Publish to PyPI                                ✅
      → pip install grncli==0.2.0
```

### Phase 4: Users Install

```bash
# From PyPI
pip install grncli
pip install grncli==0.2.0

# From GitHub Releases (offline bundle)
unzip grncli-bundle.zip
cd grncli-bundle && ./install-offline
```

---

## Hotfix Flow

For urgent fixes that skip the PR process:

```bash
git checkout main
vim grncli/auth.py                        # Fix bug
python -m pytest tests/ -v
./scripts/new-change -t bugfix -c auth -d "Fix token refresh race condition"
git commit -am "fix(auth): fix token refresh race condition"
./scripts/bump-version patch              # 0.2.0 → 0.2.1
git push && git push --tags               # → release.yml triggers
```

---

## Manual Release (Workflow Dispatch)

Trigger a release manually from GitHub UI:

```
GitHub → Actions → Release → Run workflow → Input version: "0.2.1"
```

**When to use:**
- Release workflow failed mid-way (e.g. PyPI publish timeout) — re-run with same version
- Tag exists but release workflow was not yet configured at that time
- Need to rebuild release artifacts without bumping version

90% of releases use tag trigger (via `bump-version` + push). Manual dispatch is a fallback.

---

## Changelog Management

### Adding entries

```bash
# Interactive
./scripts/new-change

# CLI args
./scripts/new-change -t feature -c vks -d "Add describe-events command"
./scripts/new-change -t bugfix -c auth -d "Fix token refresh"
./scripts/new-change -t enhancement -c configure -d "Add region validation"
```

**Change types:** `feature`, `bugfix`, `enhancement`, `api-change`

### Viewing unreleased changes

```bash
ls .changes/next-release/
cat .changes/next-release/*.json
```

### Regenerating CHANGELOG.md

```bash
./scripts/render-changelog
```

---

## Version Bumping

```bash
./scripts/bump-version patch   # 0.1.0 → 0.1.1 (bug fixes)
./scripts/bump-version minor   # 0.1.0 → 0.2.0 (new features)
./scripts/bump-version major   # 0.1.0 → 1.0.0 (breaking changes)
```

---

## CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `run-tests.yml` | PR, push to main | Test matrix: Python 3.10-3.13 × Ubuntu/macOS/Windows |
| `release.yml` | Tag push `v*`, manual dispatch | Build + GitHub Release + PyPI publish |
| `bundle-test.yml` | PR, push to main | Test offline bundle installation |
| `stale.yml` | Daily schedule | Auto-close stale issues (30 days stale, 7 days close) |

---

## Adding a New Service

Other product teams can add CLI commands:

1. Create `grncli/customizations/<service>/`
2. Write commands extending `BasicCommand`
3. Register in `grncli/handlers.py`

See `grncli/customizations/vks/` for a complete reference implementation.
