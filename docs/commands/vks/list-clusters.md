# list-clusters

## Description

List all VKS clusters. By default, automatically paginates through all pages and returns the complete result set. Use `--page` to fetch a specific page, or `--no-paginate` to return only the first page.

## Synopsis

```
grn vks list-clusters
    [--page <value>]
    [--page-size <value>]
    [--no-paginate]
```

## Options

`--page` (optional)
: Specific page number to fetch (0-based index). When provided, disables auto-pagination and returns only that page.

`--page-size` (optional)
: Number of items per page. Default: `50`.

`--no-paginate` (optional)
: Disable auto-pagination and return only the first page (page 0). Equivalent to `--page 0`.

## Examples

List all clusters (auto-paginated):

```bash
grn vks list-clusters
```

List clusters with custom page size:

```bash
grn vks list-clusters --page-size 20
```

Fetch page 2 (0-based) only:

```bash
grn vks list-clusters --page 2 --page-size 10
```

Return only the first page without auto-pagination:

```bash
grn vks list-clusters --no-paginate
```

Output as JSON:

```bash
grn vks list-clusters --output json
```
