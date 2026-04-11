# Configuration

## Initial setup

```bash
grn configure
```

This will prompt for:

```
GRN Client ID [None]: <your-client-id>
GRN Client Secret [None]: <your-client-secret>
Default region name [HCM-3]:
Default output format [json]:
```

Credentials are obtained from the [VNG Cloud IAM Portal](https://hcm-3.console.vngcloud.vn/iam/) under Service Accounts.

## Config files

Credentials and config are stored in separate files:

```ini
# ~/.greenode/credentials
[default]
client_id = 5028b2cb-cb0f-4249-ae1e-1c51b2bcf6e6
client_secret = abc123

[staging]
client_id = xxx
client_secret = yyy
```

```ini
# ~/.greenode/config
[default]
region = HCM-3
output = json

[profile staging]
region = HAN
output = table
```

Credentials file is created with `0600` permissions (owner read/write only).

## Configuration commands

```bash
grn configure              # Interactive setup
grn configure list         # Show all config values and sources
grn configure get region   # Get a specific value
grn configure set region HAN  # Set a specific value
```

### `grn configure list` output

```
          Name                   Value            Type    Location
          ----                   -----            ----    --------
       profile               <not set>            None    None
     client_id    ****************bc6e     config-file    ~/.greenode/credentials
 client_secret    ****************c123     config-file    ~/.greenode/credentials
        region                   HCM-3     config-file    ~/.greenode/config
        output                    json     config-file    ~/.greenode/config
```

## Profiles

```bash
# Configure a named profile
grn configure --profile staging

# Use a named profile
grn --profile staging vks list-clusters

# Or via environment variable
export GRN_PROFILE=staging
grn vks list-clusters
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `GRN_CLIENT_ID` | Client ID (overrides config file) |
| `GRN_CLIENT_SECRET` | Client Secret (overrides config file) |
| `GRN_DEFAULT_REGION` | Default region |
| `GRN_PROFILE` | Profile name |
| `GRN_DEFAULT_OUTPUT` | Output format |

Environment variables take priority over config file values.

## Available regions

| Region | VKS Endpoint |
|--------|-------------|
| `HCM-3` | `https://vks.api.vngcloud.vn` |
| `HAN` | `https://vks-han-1.api.vngcloud.vn` |
