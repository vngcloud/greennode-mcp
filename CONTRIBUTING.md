# Contributing to Greenode CLI

Thank you for your interest in contributing to the Greenode CLI!

## Getting Started

### Prerequisites

- Python 3.10 or later
- Git

### Setup development environment

```bash
git clone https://github.com/vngcloud/greennode-cli.git
cd greennode-cli
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Run tests

```bash
python -m pytest tests/ -v
```

## Development Workflow

### 1. Create a feature branch

```bash
git checkout develop
git pull
git checkout -b feat/your-feature-name
```

### 2. Make changes and test

```bash
# Write code
# Write tests
python -m pytest tests/ -v
```

### 3. Add a changelog entry

Every PR should include a changelog fragment:

```bash
./scripts/new-change -t feature -c vks -d "Add your feature description"
```

Change types: `feature`, `bugfix`, `enhancement`, `api-change`

### 4. Commit and push

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(vks): add describe-events command
fix(auth): fix token refresh race condition
docs(readme): update installation instructions
```

### 5. Create a Pull Request

- PR to `develop` for testing
- PR to `main` when release-ready
- CI must pass before merge
- At least 1 approval required

## Adding a New Service

Other product teams can add CLI commands:

1. Create `grncli/customizations/<service>/`
2. Write commands extending `BasicCommand` (see `grncli/customizations/vks/` for reference)
3. Register in `grncli/handlers.py`

### Command template

```python
from grncli.customizations.commands import BasicCommand, display_output

class MyCommand(BasicCommand):
    NAME = 'my-command'
    DESCRIPTION = 'Description of my command'
    ARG_TABLE = [
        {'name': 'my-arg', 'help_text': 'Argument description', 'required': True},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        client = self._session.create_client('my-service')
        result = client.get('/v1/my-endpoint')
        display_output(result, parsed_globals)
        return 0
```

## Code Style

- All source code text (messages, comments, descriptions) must be in English
- Follow existing patterns in the codebase
- Add tests for new features
- Validate user inputs (especially IDs used in URLs)
- Use `--dry-run` for create/update/delete commands
- Add `--force` to skip confirmation on delete commands

## Reporting Issues

- Use [GitHub Issues](https://github.com/vngcloud/greennode-cli/issues)
- Search existing issues before creating a new one
- Use the provided issue templates

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
