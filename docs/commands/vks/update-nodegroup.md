# update-nodegroup

## Description

Update a node group's image, node count, security groups, labels, taints, auto-scaling configuration, and upgrade strategy. The image ID is always required by the API, even when the intent is to update only other fields.

Use `--dry-run` to preview the update payload without executing it.

## Synopsis

```
grn vks update-nodegroup
    --cluster-id <value>
    --nodegroup-id <value>
    --image-id <value>
    [--num-nodes <value>]
    [--security-groups <value>]
    [--labels <value>]
    [--taints <value>]
    [--auto-scale-min <value>]
    [--auto-scale-max <value>]
    [--upgrade-strategy <value>]
    [--upgrade-max-surge <value>]
    [--upgrade-max-unavailable <value>]
    [--dry-run]
```

## Options

`--cluster-id` (required)
: ID of the cluster that owns the node group.

`--nodegroup-id` (required)
: ID of the node group to update.

`--image-id` (required)
: OS image ID. Always required by the API — pass the current image ID to leave it unchanged.

`--num-nodes` (optional)
: New desired number of nodes for the node group.

`--security-groups` (optional)
: Comma-separated list of security group IDs to replace the current set.

`--labels` (optional)
: Comma-separated `key=value` pairs to set as Kubernetes node labels (replaces existing labels).

`--taints` (optional)
: Comma-separated node taints in `key=value:effect` format (replaces existing taints).

`--auto-scale-min` (optional)
: Minimum number of nodes for the auto-scaler.

`--auto-scale-max` (optional)
: Maximum number of nodes for the auto-scaler.

`--upgrade-strategy` (optional)
: Node upgrade strategy. Accepted value: `SURGE`.

`--upgrade-max-surge` (optional)
: Maximum number of extra nodes to create during a surge upgrade.

`--upgrade-max-unavailable` (optional)
: Maximum number of nodes that may be unavailable during an upgrade.

`--dry-run` (optional)
: Print the update payload without sending the request.

## Examples

Scale a node group to 5 nodes:

```bash
grn vks update-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345 \
  --image-id img-ubuntu-22-04-k8s \
  --num-nodes 5
```

Update node image and set auto-scaling limits:

```bash
grn vks update-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345 \
  --image-id img-ubuntu-22-04-k8s-v2 \
  --auto-scale-min 2 \
  --auto-scale-max 10
```

Update labels and taints:

```bash
grn vks update-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345 \
  --image-id img-ubuntu-22-04-k8s \
  --labels env=prod,tier=app \
  --taints dedicated=gpu:NoSchedule
```

Preview the update payload (dry run):

```bash
grn vks update-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345 \
  --image-id img-ubuntu-22-04-k8s \
  --num-nodes 3 \
  --dry-run
```
