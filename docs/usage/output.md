# Output Formatting

## Output formats

```bash
grn vks list-clusters --output json    # JSON (default)
grn vks list-clusters --output table   # Table
grn vks list-clusters --output text    # Tab-separated text
```

### JSON (default)

```json
{
    "items": [
        {
            "id": "k8s-xxxxx",
            "name": "my-cluster",
            "status": "ACTIVE"
        }
    ],
    "total": 1
}
```

### Table

```
id        | name       | status
----------+------------+-------
k8s-xxxxx | my-cluster | ACTIVE
```

### Text

```
k8s-xxxxx	my-cluster	ACTIVE
```

## JMESPath query

Use `--query` to filter response data with [JMESPath](https://jmespath.org/) expressions:

```bash
# Get only cluster names
grn vks list-clusters --query "items[].name"
# ["my-cluster", "prod-cluster"]

# Get cluster status
grn vks get-cluster --cluster-id k8s-xxxxx --query "status"
# "ACTIVE"

# Filter clusters by status
grn vks list-clusters --query "items[?status=='ACTIVE'].name"
# ["my-cluster"]
```
