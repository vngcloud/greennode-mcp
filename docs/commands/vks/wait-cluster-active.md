# wait-cluster-active

## Description

Poll a VKS cluster until it reaches `ACTIVE` status. Progress is written to stderr so it does not interfere with stdout output or piping. The waiter exits with code `0` on success, and `255` if the cluster reaches `ERROR`/`FAILED` status or the maximum number of attempts is exceeded.

Default timeout: 40 attempts × 15 seconds = **10 minutes**.

## Synopsis

```
grn vks wait-cluster-active
    --cluster-id <value>
    [--delay <value>]
    [--max-attempts <value>]
```

## Options

`--cluster-id` (required)
: ID of the cluster to wait for.

`--delay` (optional)
: Seconds to wait between each poll. Default: `15`.

`--max-attempts` (optional)
: Maximum number of polling attempts before the waiter times out. Default: `40`.

## Examples

Wait for a cluster to become active (default timeout of 10 minutes):

```bash
grn vks wait-cluster-active \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345
```

Wait with shorter polling interval and more attempts (up to 20 minutes):

```bash
grn vks wait-cluster-active \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --delay 10 \
  --max-attempts 120
```

Create a cluster and wait for it to become active in one pipeline:

```bash
grn vks create-cluster \
  --name my-cluster \
  --k8s-version v1.29.1 \
  --network-type CILIUM_NATIVE_ROUTING \
  --vpc-id net-abc12345-0000-0000-0000-000000000001 \
  --subnet-id sub-abc12345-0000-0000-0000-000000000001 \
  --node-group-name default-ng \
  --flavor-id flv-2c4g \
  --image-id img-ubuntu-22-04-k8s \
  --disk-type SSD \
  --ssh-key-id key-abc12345-0000-0000-0000-000000000001 \
  --output json | jq -r '.id' \
  | xargs -I{} grn vks wait-cluster-active --cluster-id {}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0`  | Cluster reached `ACTIVE` status |
| `255` | Cluster reached `ERROR` or `FAILED` status, or waiter timed out |
