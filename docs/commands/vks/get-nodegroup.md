# get-nodegroup

## Description

Get detailed information about a specific node group within a cluster, including its status, flavor, image, disk configuration, node count, labels, and taints.

## Synopsis

```
grn vks get-nodegroup
    --cluster-id <value>
    --nodegroup-id <value>
```

## Options

`--cluster-id` (required)
: ID of the cluster that owns the node group.

`--nodegroup-id` (required)
: ID of the node group to retrieve.

## Examples

Get node group details:

```bash
grn vks get-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345
```

Get node group details as JSON:

```bash
grn vks get-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345 \
  --output json
```

Extract the node count from the response:

```bash
grn vks get-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345 \
  --output json | jq '.numNodes'
```
