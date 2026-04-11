# Global Options

Global options are placed before the service name:

```bash
grn [global-options] <service> <command> [command-options]
```

## Options

| Option | Description |
|--------|-------------|
| `--profile <name>` | Use a specific profile from credential file |
| `--region <name>` | Override region (overrides config/env settings) |
| `--output <format>` | Output format: `json`, `text`, `table` |
| `--query <expr>` | JMESPath query to filter response data |
| `--endpoint-url <url>` | Override service URL |
| `--no-verify-ssl` | Disable SSL certificate verification |
| `--debug` | Enable debug logging |
| `--cli-read-timeout <sec>` | Socket read timeout in seconds (default: 30) |
| `--cli-connect-timeout <sec>` | Socket connect timeout in seconds (default: 30) |
| `--color <on\|off\|auto>` | Color output control |
| `--version` | Display version info |

## Examples

```bash
# Use staging profile
grn --profile staging vks list-clusters

# Override region
grn --region HAN vks list-clusters

# Custom endpoint (for local testing)
grn --endpoint-url http://localhost:8080 vks list-clusters

# Disable SSL (dev only)
grn --no-verify-ssl vks list-clusters
# Warning: SSL certificate verification is disabled. This is insecure and should only be used for testing.

# Debug logging
grn --debug vks list-clusters

# Custom timeout
grn --cli-read-timeout 60 vks list-clusters
```
