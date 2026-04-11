# Contributing

See [CONTRIBUTING.md](https://github.com/vngcloud/greennode-cli/blob/main/CONTRIBUTING.md) for the full contributing guide.

## Quick start

```bash
git clone https://github.com/vngcloud/greennode-cli.git
cd greennode-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Adding a new service

1. Create `grncli/customizations/<service>/`
2. Write commands extending `BasicCommand`
3. Register in `grncli/handlers.py`

See `grncli/customizations/vks/` for a complete reference implementation.
