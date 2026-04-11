# create-nodegroup

## Description

Create a new node group within an existing VKS cluster. Node group names must be 5–15 characters, lowercase alphanumeric and hyphens, starting and ending with an alphanumeric character.

Use `--dry-run` to validate parameters (name format, disk size range, node count range) without sending a create request.

## Synopsis

```
grn vks create-nodegroup
    --cluster-id <value>
    --name <value>
    --image-id <value>
    --flavor-id <value>
    --disk-type <value>
    --ssh-key-id <value>
    [--enable-private-nodes]
    [--num-nodes <value>]
    [--disk-size <value>]
    [--security-groups <value>]
    [--subnet-id <value>]
    [--labels <value>]
    [--taints <value>]
    [--enable-encryption-volume]
    [--dry-run]
```

## Options

`--cluster-id` (required)
: ID of the cluster to add the node group to.

`--name` (required)
: Node group name. Must be 5–15 characters, lowercase alphanumeric and hyphens, starting and ending with an alphanumeric character.

`--image-id` (required)
: OS image ID for the nodes.

`--flavor-id` (required)
: Flavor (instance type) ID for the nodes.

`--disk-type` (required)
: Disk type ID for the node boot volumes.

`--ssh-key-id` (required)
: SSH key pair ID to inject into each node.

`--enable-private-nodes` (optional)
: Enable private nodes (nodes will not have public IP addresses).

`--num-nodes` (optional)
: Number of nodes to create. Accepted range: 0–10. Default: `1`.

`--disk-size` (optional)
: Boot disk size in GiB. Accepted range: 20–5000. Default: `100`.

`--security-groups` (optional)
: Comma-separated list of security group IDs to attach to the nodes (e.g. `sg-aaa111,sg-bbb222`).

`--subnet-id` (optional)
: Subnet ID for the node group. Uses the cluster subnet when not specified.

`--labels` (optional)
: Comma-separated `key=value` pairs to add as Kubernetes node labels (e.g. `env=prod,tier=app`).

`--taints` (optional)
: Comma-separated node taints in `key=value:effect` format (e.g. `dedicated=gpu:NoSchedule`).

`--enable-encryption-volume` (optional)
: Enable encryption for the node boot volumes.

`--dry-run` (optional)
: Validate parameters and print a report without sending the create request.

## Examples

Create a basic node group:

```bash
grn vks create-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --name worker-ng \
  --image-id img-ubuntu-22-04-k8s \
  --flavor-id flv-4c8g \
  --disk-type SSD \
  --ssh-key-id key-abc12345-0000-0000-0000-000000000001
```

Create a GPU node group with taints and labels:

```bash
grn vks create-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --name gpu-ng \
  --image-id img-ubuntu-22-04-k8s-gpu \
  --flavor-id flv-8c32g-gpu \
  --disk-type SSD \
  --disk-size 200 \
  --num-nodes 2 \
  --ssh-key-id key-abc12345-0000-0000-0000-000000000001 \
  --labels accelerator=nvidia,tier=gpu \
  --taints dedicated=gpu:NoSchedule \
  --enable-encryption-volume
```

Validate parameters without creating:

```bash
grn vks create-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --name worker-ng \
  --image-id img-ubuntu-22-04-k8s \
  --flavor-id flv-4c8g \
  --disk-type SSD \
  --ssh-key-id key-abc12345-0000-0000-0000-000000000001 \
  --dry-run
```
