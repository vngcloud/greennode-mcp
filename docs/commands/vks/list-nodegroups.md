# list-nodegroups

## Description

List all node groups belonging to a cluster. By default, automatically paginates through all pages and returns the complete result set. Use `--page` to fetch a specific page, or `--no-paginate` to return only the first page.

## Synopsis

```
grn vks list-nodegroups
    --cluster-id <value>
    [--page <value>]
    [--page-size <value>]
    [--no-paginate]
```

## Options

`--cluster-id` (required)
: ID of the cluster whose node groups to list.

`--page` (optional)
: Specific page number to fetch (0-based index). When provided, disables auto-pagination and returns only that page.

`--page-size` (optional)
: Number of items per page. Default: `50`.

`--no-paginate` (optional)
: Disable auto-pagination and return only the first page (page 0).

## Examples

List all node groups for a cluster:

```bash
grn vks list-nodegroups --cluster-id cls-abc12345-6789-def0-1234-abcdef012345
```

List node groups with a custom page size:

```bash
grn vks list-nodegroups \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --page-size 20
```

Fetch only the first page:

```bash
grn vks list-nodegroups \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --no-paginate
```

Output as JSON and count node groups:

```bash
grn vks list-nodegroups \
  --cluster-id cls-abc12345-6789-def0-1234-abcdef012345 \
  --output json | jq '.items | length'
```
