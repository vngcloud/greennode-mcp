# Dry-run & Confirmation

## Dry-run

All create, update, and delete commands support `--dry-run`:

```bash
# Validate create parameters without calling API
grn vks create-cluster --dry-run --name my-cluster --k8s-version v1.30 ...
grn vks create-nodegroup --dry-run --cluster-id k8s-xxxxx --name workers ...

# Preview update parameters
grn vks update-cluster --dry-run --cluster-id k8s-xxxxx --k8s-version v1.31 --whitelist-node-cidrs 0.0.0.0/0
grn vks update-nodegroup --dry-run --cluster-id k8s-xxxxx --nodegroup-id ng-xxxxx --image-id img-xxxxx

# Preview what will be deleted
grn vks delete-cluster --dry-run --cluster-id k8s-xxxxx
grn vks delete-nodegroup --dry-run --cluster-id k8s-xxxxx --nodegroup-id ng-xxxxx
```

### Create dry-run

Validates parameters offline:

- Cluster/nodegroup name format
- Disk size range (20-5000 GiB)
- Number of nodes range (0-10)
- CIDR requirement for CALICO/CILIUM_OVERLAY networks

### Delete dry-run

Fetches and displays resources that will be deleted:

```
=== DRY RUN: The following resources will be deleted ===

Cluster:
  ID:      k8s-xxxxx
  Name:    my-cluster
  Status:  ACTIVE
  Version: v1.30.10
  Nodes:   3

Node groups (1):
  - default (ID: ng-xxxxx, nodes: 3)

Run without --dry-run to delete.
```

## Delete confirmation

Delete commands show a preview and prompt for confirmation:

```bash
grn vks delete-cluster --cluster-id k8s-xxxxx
# The following resources will be deleted:
# ...
# Are you sure you want to delete this cluster? (yes/no): yes
```

### Skip confirmation

Use `--force` to skip the confirmation prompt (for scripting):

```bash
grn vks delete-cluster --cluster-id k8s-xxxxx --force
```
