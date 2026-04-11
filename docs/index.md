# Greenode CLI

Universal Command Line Interface for Green Node.

The Greenode CLI (`grn`) is a unified tool to manage your Green Node services from the command line. It is modeled after the AWS CLI architecture and supports hand-written commands, with VKS (VNG Kubernetes Service) as the first service.

## Quick Start

```bash
# Install
pip install grncli

# Configure credentials
grn configure

# List your VKS clusters
grn vks list-clusters

# Get cluster details
grn vks get-cluster --cluster-id <id>
```

## Features

- **VKS Management** — Full cluster and node group lifecycle (create, get, update, delete)
- **Multiple Output Formats** — JSON, table, and text with JMESPath query filtering
- **Auto-pagination** — List commands fetch all pages by default
- **Dry-run** — Validate parameters before create/update/delete
- **Delete Confirmation** — Preview and confirm before destructive operations
- **Waiter Commands** — Wait for async operations to complete
- **Profile Support** — Multiple credential profiles for different environments
- **Retry with Backoff** — Automatic retry for transient errors (5xx, timeouts)
- **Security** — Credentials masked in output, input validation, SSL by default

## Adding New Services

Other product teams can add CLI commands for their service. See [Contributing](development/contributing.md) for details.
