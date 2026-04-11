# Greenode CLI (`grn`)

Universal Command Line Interface for Greenode (VNG Cloud).

## Installation

### Prerequisites

- Python 3.10 or later
- `pip` 21.0 or greater
- `setuptools` 68.0 or greater

### Install from PyPI

The recommended way to install the Greenode CLI is to use `pip` in a `virtualenv`:

```bash
python -m pip install grncli
```

or, if you are not installing in a `virtualenv`, to install globally:

```bash
sudo python -m pip install grncli
```

or for your user:

```bash
python -m pip install --user grncli
```

If you have the grncli package installed and want to upgrade to the latest version:

```bash
python -m pip install --upgrade grncli
```

### Install from source

```bash
git clone https://github.com/vngcloud/greennode-cli.git
cd greennode-cli
python -m pip install .
```

To install with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

### Bundled installer

On Linux and macOS, the Greenode CLI can be installed using a standalone installer that creates an isolated virtualenv:

```bash
./scripts/install
```

This installs to `~/.local/lib/greenode` and symlinks `grn` to `~/.local/bin/`. Make sure `~/.local/bin` is in your `PATH`.

### Offline install

For environments without internet access, you can build a self-contained bundle:

```bash
# On a machine with internet access
./scripts/make-bundle

# Transfer dist/grncli-bundle.zip to target machine, then:
unzip grncli-bundle.zip
cd grncli-bundle
./install-offline
```

If you want to run the `develop` branch of the Greenode CLI, see the [Development Guide](docs/DEVELOPMENT.md).

## Configuration

```bash
grn configure
```

This will prompt for:
- GRN Client ID (from IAM Service Account)
- GRN Client Secret
- Default region name (default: HCM-3)
- Default output format (default: json)

Credentials are stored in `~/.greenode/credentials` and config in `~/.greenode/config`.

### Configuration commands

```bash
grn configure              # Interactive setup
grn configure list         # Show all config values and sources
grn configure get region   # Get a specific value
grn configure set region HAN  # Set a specific value
```

### Profiles

```bash
grn configure --profile staging   # Configure a named profile
grn --profile staging vks list-clusters  # Use a named profile
export GRN_PROFILE=staging        # Or via environment variable
```

### Environment variables

| Variable | Description |
|----------|-------------|
| `GRN_CLIENT_ID` | Client ID (overrides config file) |
| `GRN_CLIENT_SECRET` | Client Secret (overrides config file) |
| `GRN_DEFAULT_REGION` | Default region |
| `GRN_PROFILE` | Profile name |
| `GRN_DEFAULT_OUTPUT` | Output format |

## Usage

### Help

```bash
grn                        # Show available commands
grn help                   # Same
grn vks                    # Show available VKS commands
grn vks create-cluster help  # Show command help with required/optional args
```

### Cluster commands

```bash
grn vks list-clusters
grn vks get-cluster --cluster-id <id>
grn vks create-cluster \
  --name <name> \
  --k8s-version <version> \
  --network-type CILIUM_OVERLAY \
  --vpc-id <vpc-id> \
  --subnet-id <subnet-id> \
  --cidr 192.168.0.0/16 \
  --node-group-name <ng-name> \
  --flavor-id <flavor-id> \
  --image-id <image-id> \
  --disk-type <disk-type-id> \
  --ssh-key-id <ssh-key-id>
grn vks update-cluster --cluster-id <id> --k8s-version <version> --whitelist-node-cidrs 0.0.0.0/0
grn vks delete-cluster --cluster-id <id>              # Prompts for confirmation
grn vks delete-cluster --cluster-id <id> --force      # Skip confirmation
grn vks delete-cluster --cluster-id <id> --dry-run    # Preview only
```

### Node group commands

```bash
grn vks list-nodegroups --cluster-id <id>
grn vks get-nodegroup --cluster-id <id> --nodegroup-id <ng-id>
grn vks create-nodegroup \
  --cluster-id <id> \
  --name <name> \
  --image-id <image-id> \
  --flavor-id <flavor-id> \
  --disk-type <disk-type-id> \
  --ssh-key-id <ssh-key-id>
grn vks update-nodegroup --cluster-id <id> --nodegroup-id <ng-id> --image-id <image-id>
grn vks delete-nodegroup --cluster-id <id> --nodegroup-id <ng-id>          # Prompts for confirmation
grn vks delete-nodegroup --cluster-id <id> --nodegroup-id <ng-id> --force  # Skip confirmation
```

### Dry-run

All create, update, and delete commands support `--dry-run`:

```bash
# Validate create parameters without calling API
grn vks create-cluster --dry-run --name <name> --k8s-version <ver> ...
grn vks create-nodegroup --dry-run --cluster-id <id> --name <name> ...

# Preview update parameters
grn vks update-cluster --dry-run --cluster-id <id> --k8s-version <ver> --whitelist-node-cidrs 0.0.0.0/0
grn vks update-nodegroup --dry-run --cluster-id <id> --nodegroup-id <ng-id> --image-id <img>

# Preview what will be deleted
grn vks delete-cluster --dry-run --cluster-id <id>
grn vks delete-nodegroup --dry-run --cluster-id <id> --nodegroup-id <ng-id>
```

### Delete confirmation

Delete commands show a preview and prompt for confirmation:

```bash
grn vks delete-cluster --cluster-id <id>
  The following resources will be deleted:
  Cluster:
    ID:   k8s-xxx
    Name: my-cluster
    ...
  Are you sure you want to delete this cluster? (yes/no): yes

# Skip confirmation (for scripting)
grn vks delete-cluster --cluster-id <id> --force
```

### Output format

```bash
grn vks list-clusters --output json    # JSON (default)
grn vks list-clusters --output table   # Table
grn vks list-clusters --output text    # Tab-separated text
grn vks list-clusters --query "items[].name"  # JMESPath filtering
```

### Pagination

List commands auto-paginate by default (fetch all pages):

```bash
grn vks list-clusters                  # Auto-paginate: returns all clusters
grn vks list-clusters --no-paginate    # First page only
grn vks list-clusters --page 2         # Specific page (0-based)
grn vks list-clusters --page-size 20   # Custom page size
```

### Waiter commands

Wait for async operations to complete:

```bash
grn vks wait-cluster-active --cluster-id <id>    # Wait until cluster is ACTIVE
grn vks wait-cluster-active --cluster-id <id> --delay 30 --max-attempts 20
```

### Global options

```bash
grn --region HAN vks list-clusters           # Override region
grn --endpoint-url http://localhost:8080 vks list-clusters  # Custom endpoint
grn --no-verify-ssl vks list-clusters        # Disable SSL verification
grn --debug vks list-clusters                # Debug logging
grn --cli-read-timeout 60 vks list-clusters  # Custom read timeout (seconds)
```

## Project structure

```
greenode-cli/
├── bin/grn                          # Entry point script
├── grncli/
│   ├── clidriver.py                 # CLIDriver — main orchestrator
│   ├── session.py                   # Config, credentials, region management
│   ├── auth.py                      # OAuth2 Client Credentials (IAM)
│   ├── client.py                    # HTTP client with retry and auto-refresh
│   ├── formatter.py                 # JSON, Table, Text output formatters
│   ├── data/cli.json                # Global CLI options definition
│   └── customizations/
│       ├── commands.py              # BasicCommand base class
│       ├── configure/               # grn configure commands
│       └── vks/                     # VKS service commands
├── tests/
├── scripts/
│   ├── install                      # Standalone installer
│   ├── make-bundle                  # Offline bundle creator
│   └── ci/                          # CI scripts
├── setup.py                         # Package configuration
├── setup.cfg                        # Wheel and tool settings
├── pyproject.toml                   # Build system config
├── requirements.txt                 # Production dependencies
└── LICENSE                          # Apache 2.0
```

## Adding a new service

Other teams can add CLI commands for their product by:

1. Create `grncli/customizations/<service>/`
2. Write commands extending `BasicCommand`
3. Register in `grncli/handlers.py`

See `grncli/customizations/vks/` for reference.

## Release process

### Adding changelog entries

```bash
./scripts/new-change                          # Interactive
./scripts/new-change -t feature -c vks -d "Add new command"  # CLI args
```

### Creating a release

```bash
./scripts/bump-version patch   # 0.1.0 → 0.1.1
./scripts/bump-version minor   # 0.1.0 → 0.2.0
./scripts/bump-version major   # 0.1.0 → 1.0.0
git push && git push --tags    # Triggers GitHub Actions release
```

### CI/CD workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `run-tests.yml` | PR, push to main | Test matrix (Python 3.10-3.13 × Ubuntu/macOS/Windows) |
| `release.yml` | Tag push `v*`, manual dispatch | Build + GitHub Release + PyPI publish |
| `bundle-test.yml` | PR, push to main | Test offline bundle installation |
| `stale.yml` | Daily schedule | Auto-close stale issues |

## Security

- Credentials stored in `~/.greenode/credentials` with `0600` permissions (owner read/write only)
- Credentials masked in `grn configure list` and `grn configure get` output
- Cluster ID and node group ID inputs validated (alphanumeric + hyphens only) to prevent path traversal
- SSL verification enabled by default; `--no-verify-ssl` prints a warning to stderr
- Tokens stored in memory only, never written to disk or logged
- Dependencies pinned to major versions to prevent supply chain issues

## License

Apache License 2.0 — see [LICENSE](LICENSE).
