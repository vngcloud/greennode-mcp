# create-cluster

## Description

Create a new VKS cluster with an initial default node group. The command provisions both the control plane and the first node group in a single call.

Cluster names must be 5–20 characters, lowercase alphanumeric and hyphens, starting and ending with an alphanumeric character. Node group names follow the same pattern with a length of 5–15 characters.

When `--network-type` is `CALICO` or `CILIUM_OVERLAY`, the `--cidr` option is required. By default, both the load balancer plugin and the block store CSI plugin are enabled; use the `--no-*` flags to disable them.

Use `--dry-run` to validate all parameters without sending a create request.

## Synopsis

```
grn vks create-cluster
    --name <value>
    --k8s-version <value>
    --network-type <value>
    --vpc-id <value>
    --subnet-id <value>
    --node-group-name <value>
    --flavor-id <value>
    --image-id <value>
    --disk-type <value>
    --ssh-key-id <value>
    [--cidr <value>]
    [--description <value>]
    [--enable-private-cluster]
    [--release-channel <value>]
    [--enabled-load-balancer-plugin]
    [--no-load-balancer-plugin]
    [--enabled-block-store-csi-plugin]
    [--no-block-store-csi-plugin]
    [--disk-size <value>]
    [--num-nodes <value>]
    [--enable-private-nodes]
    [--security-groups <value>]
    [--labels <value>]
    [--taints <value>]
    [--dry-run]
```

## Options

**Cluster settings**

`--name` (required)
: Cluster name. Must be 5–20 characters, lowercase alphanumeric and hyphens, starting and ending with an alphanumeric character.

`--k8s-version` (required)
: Kubernetes version for the cluster (e.g. `v1.29.1`).

`--network-type` (required)
: Network type for the cluster. Accepted values: `CALICO`, `CILIUM_OVERLAY`, `CILIUM_NATIVE_ROUTING`.

`--vpc-id` (required)
: VPC ID where the cluster will be provisioned.

`--subnet-id` (required)
: Subnet ID for the cluster control plane and the default node group.

`--cidr` (optional)
: Pod CIDR block. Required when `--network-type` is `CALICO` or `CILIUM_OVERLAY` (e.g. `10.96.0.0/12`).

`--description` (optional)
: Human-readable description for the cluster.

`--enable-private-cluster` (optional)
: Enable private cluster mode (control plane not accessible from the public internet).

`--release-channel` (optional)
: Release channel for automatic upgrades. Accepted values: `RAPID`, `STABLE`. Default: `STABLE`.

`--enabled-load-balancer-plugin` (optional)
: Explicitly enable the load balancer plugin (enabled by default).

`--no-load-balancer-plugin` (optional)
: Disable the load balancer plugin.

`--enabled-block-store-csi-plugin` (optional)
: Explicitly enable the block store CSI plugin (enabled by default).

`--no-block-store-csi-plugin` (optional)
: Disable the block store CSI plugin.

**Node group settings**

`--node-group-name` (required)
: Name of the initial node group. Must be 5–15 characters, lowercase alphanumeric and hyphens, starting and ending with an alphanumeric character.

`--flavor-id` (required)
: Flavor (instance type) ID for the nodes.

`--image-id` (required)
: OS image ID for the nodes.

`--disk-type` (required)
: Disk type ID for the node boot volumes.

`--ssh-key-id` (required)
: SSH key pair ID to inject into each node.

`--disk-size` (optional)
: Boot disk size in GiB. Accepted range: 20–5000. Default: `100`.

`--num-nodes` (optional)
: Number of nodes to create in the default node group. Accepted range: 0–10. Default: `1`.

`--enable-private-nodes` (optional)
: Enable private nodes (nodes will not have public IP addresses).

`--security-groups` (optional)
: Comma-separated list of security group IDs to attach to the nodes (e.g. `sg-aaa111,sg-bbb222`).

`--labels` (optional)
: Comma-separated `key=value` pairs to add as Kubernetes node labels (e.g. `env=prod,tier=app`).

`--taints` (optional)
: Comma-separated node taints in `key=value:effect` format (e.g. `dedicated=gpu:NoSchedule`).

`--dry-run` (optional)
: Validate all parameters and print a report without sending the create request.

## Examples

Create a minimal cluster with CILIUM_NATIVE_ROUTING:

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
  --ssh-key-id key-abc12345-0000-0000-0000-000000000001
```

Create a cluster with CALICO network type (CIDR required):

```bash
grn vks create-cluster \
  --name prod-cluster \
  --k8s-version v1.29.1 \
  --network-type CALICO \
  --cidr 10.96.0.0/12 \
  --vpc-id net-abc12345-0000-0000-0000-000000000001 \
  --subnet-id sub-abc12345-0000-0000-0000-000000000001 \
  --node-group-name prod-ng \
  --flavor-id flv-4c8g \
  --image-id img-ubuntu-22-04-k8s \
  --disk-type SSD \
  --disk-size 200 \
  --num-nodes 3 \
  --ssh-key-id key-abc12345-0000-0000-0000-000000000001 \
  --labels env=prod,tier=app \
  --taints dedicated=gpu:NoSchedule
```

Validate parameters without creating (dry run):

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
  --dry-run
```
