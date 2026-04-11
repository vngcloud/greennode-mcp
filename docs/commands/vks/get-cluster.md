# get-cluster

## Description

Get detailed information about a specific VKS cluster, including its status, Kubernetes version, network configuration, node group count, and plugin state.

## Synopsis

```
grn vks get-cluster
    --cluster-id <value>
```

## Options

`--cluster-id` (required)
: The ID of the cluster to retrieve.

## Examples

Get cluster details:

```bash
grn vks get-cluster --cluster-id cls-abc12345-6789-def0-1234-abcdef012345
```

Get cluster details and output as JSON:

```bash
grn vks get-cluster --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 --output json
```

Use with `jq` to extract just the cluster status:

```bash
grn vks get-cluster --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 --output json \
  | jq '.status'
```
