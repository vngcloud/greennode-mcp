# Release Process

## Adding changelog entries

Every PR should include a changelog fragment:

```bash
./scripts/new-change                          # Interactive
./scripts/new-change -t feature -c vks -d "Add new command"  # CLI args
```

Change types: `feature`, `bugfix`, `enhancement`, `api-change`

## Creating a release

```bash
./scripts/bump-version patch   # 0.1.0 → 0.1.1
./scripts/bump-version minor   # 0.1.0 → 0.2.0
./scripts/bump-version major   # 0.1.0 → 1.0.0
git push && git push --tags    # Triggers GitHub Actions release
```

The `bump-version` script automatically:

1. Updates version in `grncli/__init__.py`
2. Merges changelog fragments into versioned file
3. Regenerates `CHANGELOG.md`
4. Commits and tags

## CI/CD workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `run-tests.yml` | PR, push to main/develop | Test matrix: Python 3.10-3.13 × Ubuntu/macOS/Windows |
| `release.yml` | Tag push `v*`, manual dispatch | Build + GitHub Release + PyPI publish |
| `bundle-test.yml` | PR, push to main/develop | Test offline bundle installation |
| `stale.yml` | Daily schedule | Auto-close stale issues |

## Release flow

```
Developer workflow:
1. During development: ./scripts/new-change (add fragments per PR)
2. Ready to release:   ./scripts/bump-version minor
3. Push:               git push && git push --tags

GitHub Actions (automatic):
4. run-tests     → Tests pass
5. release       → Build wheel + sdist + bundle
6.               → Create GitHub Release with artifacts
7.               → Publish to PyPI (requires approval)
```
