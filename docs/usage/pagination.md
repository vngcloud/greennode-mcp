# Pagination

List commands auto-paginate by default, fetching all pages and merging results.

## Default behavior

```bash
# Returns all clusters (auto-pagination)
grn vks list-clusters
```

## Disable auto-pagination

```bash
# First page only
grn vks list-clusters --no-paginate

# Specific page (0-based)
grn vks list-clusters --page 2

# Custom page size (default: 50)
grn vks list-clusters --page-size 20
```

!!! note
    When `--page` is specified, auto-pagination is disabled and only that page is returned.
