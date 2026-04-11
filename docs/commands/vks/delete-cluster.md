# delete-cluster

## Description

Delete a VKS cluster and all of its associated node groups. Before executing the delete, the command always fetches and displays a preview of the cluster and node groups that will be removed.

Unless `--force` is provided, you will be prompted to type `yes` to confirm. Use `--dry-run` to see the preview without being prompted and without deleting anything.

**This action is irreversible.**

## Synopsis

```
grn vks delete-cluster
    --cluster-id <value>
    [--dry-run]
    [--force]
```

## Options

`--cluster-id` (required)
: ID of the cluster to delete.

`--dry-run` (optional)
: Display the resources that would be deleted without executing the delete request.

`--force` (optional)
: Skip the interactive confirmation prompt and delete immediately.

## Examples

Delete a cluster interactively (prompts for confirmation):

```bash
grn vks delete-cluster --cluster-id cls-abc12345-6789-def0-1234-abcdef012345
```

Preview what will be deleted without deleting:

```bash
grn vks delete-cluster \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --dry-run
```

Delete without confirmation (for use in scripts):

```bash
grn vks delete-cluster \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --force
```
