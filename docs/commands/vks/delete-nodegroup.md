# delete-nodegroup

## Description

Delete a specific node group from a VKS cluster. Before executing, the command always fetches and displays a preview of the node group that will be removed (name, status, node count).

Unless `--force` is provided, you will be prompted to type `yes` to confirm. Use `--dry-run` to see the preview without being prompted and without deleting anything. Use `--force-delete` to instruct the API to perform a forced deletion.

**This action is irreversible.**

## Synopsis

```
grn vks delete-nodegroup
    --cluster-id <value>
    --nodegroup-id <value>
    [--force-delete]
    [--dry-run]
    [--force]
```

## Options

`--cluster-id` (required)
: ID of the cluster that owns the node group.

`--nodegroup-id` (required)
: ID of the node group to delete.

`--force-delete` (optional)
: Instruct the API to perform a forced deletion of the node group.

`--dry-run` (optional)
: Display the node group that would be deleted without executing the delete request.

`--force` (optional)
: Skip the interactive confirmation prompt and delete immediately.

## Examples

Delete a node group interactively (prompts for confirmation):

```bash
grn vks delete-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345
```

Preview what will be deleted without deleting:

```bash
grn vks delete-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345 \
  --dry-run
```

Delete without confirmation (for use in scripts):

```bash
grn vks delete-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345 \
  --force
```

Force-delete a stuck node group without confirmation:

```bash
grn vks delete-nodegroup \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --nodegroup-id ng-abc12345-6789-def0-1234-abcdef012345 \
  --force-delete \
  --force
```
