# update-cluster

## Description

Update a VKS cluster's Kubernetes version, whitelist CIDRs, and plugin configuration. The Kubernetes version and at least one whitelist CIDR are always required by the API, even when only updating plugin settings.

Use `--dry-run` to preview the update request without executing it.

## Synopsis

```
grn vks update-cluster
    --cluster-id <value>
    --k8s-version <value>
    --whitelist-node-cidrs <value>
    [--enabled-load-balancer-plugin]
    [--no-load-balancer-plugin]
    [--enabled-block-store-csi-plugin]
    [--no-block-store-csi-plugin]
    [--dry-run]
```

## Options

`--cluster-id` (required)
: ID of the cluster to update.

`--k8s-version` (required)
: Target Kubernetes version (e.g. `v1.29.1`). Must be the same or a higher patch/minor version than the current version.

`--whitelist-node-cidrs` (required)
: Comma-separated list of CIDRs allowed to communicate with cluster nodes. At least one value is required (e.g. `10.0.0.0/8,192.168.0.0/16`).

`--enabled-load-balancer-plugin` (optional)
: Enable the load balancer plugin.

`--no-load-balancer-plugin` (optional)
: Disable the load balancer plugin.

`--enabled-block-store-csi-plugin` (optional)
: Enable the block store CSI plugin.

`--no-block-store-csi-plugin` (optional)
: Disable the block store CSI plugin.

`--dry-run` (optional)
: Print the update payload without sending the request.

## Examples

Upgrade Kubernetes version and set whitelist CIDRs:

```bash
grn vks update-cluster \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --k8s-version v1.30.0 \
  --whitelist-node-cidrs 10.0.0.0/8,192.168.0.0/16
```

Update cluster and disable the load balancer plugin:

```bash
grn vks update-cluster \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --k8s-version v1.29.1 \
  --whitelist-node-cidrs 10.0.0.0/8 \
  --no-load-balancer-plugin
```

Preview what would be sent (dry run):

```bash
grn vks update-cluster \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --k8s-version v1.30.0 \
  --whitelist-node-cidrs 10.0.0.0/8 \
  --dry-run
```
