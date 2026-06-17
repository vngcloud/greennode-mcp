# Design: `generate_app_manifest` tool for VKS MCP

Date: 2026-06-17

## Context

The VKS MCP server's k8s handler was ported from AWS Labs `eks-mcp-server` and
has the same 6 k8s tools — except EKS also ships `generate_app_manifest`, which
VKS lacks. This tool scaffolds a Kubernetes Deployment + LoadBalancer Service
manifest from a few parameters and writes it to disk, to be applied later with
`apply_yaml`. This design ports that feature to VKS, staying faithful to the EKS
source while adapting the LoadBalancer annotation to VKS.

Reference: `src/eks-mcp-server/awslabs/eks_mcp_server/k8s_handler.py`
(`generate_app_manifest`, `_load_yaml_template`) and its
`templates/k8s-templates/{deployment,service}.yaml`.

## Goal

Add a `generate_app_manifest` tool to the VKS k8s handler that generates a
Deployment + Service (`type: LoadBalancer`) manifest and writes it to an
absolute output directory, so users can `apply_yaml` it.

## Non-goals

- No apply/deploy from this tool (that is `apply_yaml`'s job).
- No exhaustive VKS LB annotations — only the `scheme` annotation is templated;
  users add others (`load-balancer-id`, healthcheck-*, etc.) by editing the file.
- No `CallToolResult` return — VKS convention is to return a markdown `str`.

## VKS specifics (sourced, not invented)

From `docs context vks-network-full.md`, the VKS LoadBalancer Controller uses
annotation **`vks.vngcloud.vn/scheme`** on a `type: LoadBalancer` Service:
default `internet-facing`, can be `internal`. This is the VKS equivalent of AWS's
`service.beta.kubernetes.io/aws-load-balancer-scheme`.

## Tool signature

In `greennode/vks_mcp_server/k8s_handler.py`, registered in `K8sHandler.__init__`
as `generate_app_manifest`:

```python
async def generate_app_manifest(
    self,
    app_name: str = Field(..., description="Application name; used for Deployment/Service names and labels."),
    image_uri: str = Field(..., description="Full container image URI with tag, e.g. 'vcr.vngcloud.vn/<repo>:<tag>'."),
    output_dir: str = Field(..., description="Absolute path to the directory to save the manifest file."),
    port: int = Field(80, ge=1, le=65535, description="Container/Service port the application listens on."),
    replicas: int = Field(2, ge=1, description="Number of replicas to deploy."),
    cpu: str = Field("100m", description="CPU request/limit per container, e.g. '100m', '500m'."),
    memory: str = Field("128Mi", description="Memory request/limit per container, e.g. '128Mi', '1Gi'."),
    namespace: str = Field("default", description="Kubernetes namespace to deploy to."),
    load_balancer_scheme: Literal["internet-facing", "internal"] = Field(
        "internal",
        description="VKS LoadBalancer scheme, rendered as the vks.vngcloud.vn/scheme annotation. 'internal' = private VPC only; 'internet-facing' = public.",
    ),
) -> str:
```

Returns a markdown string: a success line + the saved absolute file path + the
generated YAML in a fenced block.

## Behavior

1. Guard: if `not self.allow_write` → `raise RuntimeError("Write access denied:
   generate_app_manifest requires --allow-write flag.")`, matching how `apply_yaml`
   in this handler signals denial (FastMCP wraps the exception into an error result).
2. Validate `output_dir` is absolute (`os.path.isabs`) → else
   `raise RuntimeError(f"Path must be absolute: {output_dir}")` (mirrors `apply_yaml`).
3. Validate `app_name` against RFC 1123 DNS-label rules via a ported
   `_validate_app_name` static method (≤63 chars, `^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$`);
   on failure `raise ValueError(<message>)`. This also prevents path/injection abuse.
4. Render templates via a ported `_load_yaml_template(template_files, values)`:
   read each template, `str.replace` placeholders, join with `\n---\n`.
   (Drop EKS's `_remove_checkov_skip_annotations` — VKS templates carry no
   checkov annotations.)
5. `os.makedirs(output_dir, exist_ok=True)`; write to
   `<output_dir>/<app_name>-manifest.yaml`.
6. Return the markdown result (path + YAML).

Placeholders substituted: `APP_NAME`, `NAMESPACE`, `REPLICAS`, `IMAGE_URI`,
`PORT`, `CPU`, `MEMORY`, `LOAD_BALANCER_SCHEME`.

## Templates

New dir `greennode/vks_mcp_server/templates/k8s-templates/`:

- `deployment.yaml`: mirrors EKS (apiVersion apps/v1; labels
  `app.kubernetes.io/name: APP_NAME`; `replicas: REPLICAS`; container
  `image: IMAGE_URI`, `imagePullPolicy: Always`, `containerPort: PORT`;
  `securityContext.capabilities.drop: [NET_RAW]`; resources requests=limits with
  `cpu: CPU`, `memory: MEMORY`). No checkov annotations.
- `service.yaml`: `type: LoadBalancer`; `annotations: { vks.vngcloud.vn/scheme: LOAD_BALANCER_SCHEME }`;
  `ports: [{ port: PORT, targetPort: PORT, protocol: TCP }]`;
  `selector: { app.kubernetes.io/name: APP_NAME }`.

## Packaging

Templates are non-`.py` data inside the package. At runtime the loader resolves
paths relative to `__file__`, so editable/`uv run` works without extra config.
For wheel builds, add a hatchling force-include so the templates ship:

```toml
[tool.hatch.build.targets.wheel.force-include]
"greennode/vks_mcp_server/templates" = "greennode/vks_mcp_server/templates"
```

## Testing

New `tests/test_generate_app_manifest.py`:
- Write-guard: with `allow_write=False`, `pytest.raises(RuntimeError, match="allow-write")`
  and no file is written.
- Relative `output_dir` → `pytest.raises(RuntimeError, match="absolute")`, no file written.
- Invalid `app_name` (e.g. `Bad_Name`) → `pytest.raises(ValueError)`.
- Happy path (`allow_write=True`, `tmp_path` as output_dir): file
  `<app_name>-manifest.yaml` is created; content contains the app name, image,
  `replicas: <n>`, `type: LoadBalancer`, and
  `vks.vngcloud.vn/scheme: <scheme>`; the YAML parses as two documents.

In `tests/test_tool_schemas.py`:
- `generate_app_manifest` is registered (with `allow_write=True`); its
  `load_balancer_scheme` property is an enum of
  `{internet-facing, internal}`; `port` has `minimum=1`/`maximum=65535`;
  `replicas` has `minimum=1`.

Run from the product dir: `cd src/vks-mcp-server && uv run pytest tests/ -v`.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Naive `str.replace` mis-substitutes a token | Placeholders are unique uppercase tokens only present as values in the templates (same approach as EKS) |
| Templates missing from wheel | hatchling `force-include` for the templates dir |
| Inventing VKS LB annotation | Use `vks.vngcloud.vn/scheme` confirmed in vks-network doc; template only this one |

## Out of scope / future

- Additional VKS LB annotations (healthcheck, pool-algorithm, certificate-ids…)
  as optional parameters.
- Ingress/ALB manifest generation.
