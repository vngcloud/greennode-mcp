# generate_app_manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `generate_app_manifest` tool to the VKS MCP k8s handler that scaffolds a Deployment + LoadBalancer Service manifest and writes it to disk, ported from AWS eks-mcp-server and adapted to VKS.

**Architecture:** Two YAML templates with uppercase placeholders are rendered by a simple `str.replace` loader and concatenated with `---`. The tool guards on `--allow-write`, validates an absolute `output_dir` and an RFC-1123 `app_name`, writes `<app_name>-manifest.yaml`, and returns a markdown string (path + YAML). The VKS LoadBalancer scheme is set via the `vks.vngcloud.vn/scheme` annotation.

**Tech Stack:** Python, FastMCP (mcp 1.27.0), Pydantic v2, hatchling, pytest + pytest-asyncio, PyYAML.

**Spec:** `docs/superpowers/specs/2026-06-17-generate-app-manifest-design.md`

All paths below are relative to the repo root `/Users/lap16104/Documents/vks-skill/greenode-mcp`. The package lives under `src/vks-mcp-server/`. Run tests from there: `cd src/vks-mcp-server && uv run pytest`. Commit ONLY the files named in each task (never `git add -A`).

---

## File structure

- Create: `src/vks-mcp-server/greennode/vks_mcp_server/templates/k8s-templates/deployment.yaml`
- Create: `src/vks-mcp-server/greennode/vks_mcp_server/templates/k8s-templates/service.yaml`
- Modify: `src/vks-mcp-server/pyproject.toml` (hatchling force-include for the templates dir)
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/k8s_handler.py` (`import re`; register tool; add `_validate_app_name`, `_load_yaml_template`, `generate_app_manifest`)
- Create: `src/vks-mcp-server/tests/test_generate_app_manifest.py`
- Modify: `src/vks-mcp-server/tests/test_tool_schemas.py` (schema assertions)

---

## Task 1: Templates + packaging

**Files:**
- Create: `src/vks-mcp-server/greennode/vks_mcp_server/templates/k8s-templates/deployment.yaml`
- Create: `src/vks-mcp-server/greennode/vks_mcp_server/templates/k8s-templates/service.yaml`
- Modify: `src/vks-mcp-server/pyproject.toml`

- [ ] **Step 1: Create `deployment.yaml`**

Path: `src/vks-mcp-server/greennode/vks_mcp_server/templates/k8s-templates/deployment.yaml`

```yaml
# Kubernetes Deployment template (placeholders substituted by generate_app_manifest)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: APP_NAME
  namespace: NAMESPACE
  labels:
    app.kubernetes.io/name: APP_NAME
spec:
  replicas: REPLICAS
  selector:
    matchLabels:
      app.kubernetes.io/name: APP_NAME
  template:
    metadata:
      labels:
        app.kubernetes.io/name: APP_NAME
    spec:
      containers:
      - name: APP_NAME
        image: IMAGE_URI
        imagePullPolicy: Always
        ports:
        - containerPort: PORT
        securityContext:
          capabilities:
            drop:
            - NET_RAW
        resources:
          requests:
            cpu: CPU
            memory: MEMORY
          limits:
            cpu: CPU
            memory: MEMORY
```

- [ ] **Step 2: Create `service.yaml`**

Path: `src/vks-mcp-server/greennode/vks_mcp_server/templates/k8s-templates/service.yaml`

```yaml
# Kubernetes Service template (VKS LoadBalancer; placeholders substituted by generate_app_manifest)
apiVersion: v1
kind: Service
metadata:
  name: APP_NAME
  namespace: NAMESPACE
  labels:
    app.kubernetes.io/name: APP_NAME
  annotations:
    vks.vngcloud.vn/scheme: LOAD_BALANCER_SCHEME
spec:
  type: LoadBalancer
  ports:
  - port: PORT
    targetPort: PORT
    protocol: TCP
  selector:
    app.kubernetes.io/name: APP_NAME
```

- [ ] **Step 3: Add hatchling force-include so templates ship in the wheel**

In `src/vks-mcp-server/pyproject.toml`, find:

```toml
[tool.hatch.build.targets.wheel]
packages = ["greennode"]
```

Add immediately after it:

```toml
[tool.hatch.build.targets.wheel.force-include]
"greennode/vks_mcp_server/templates" = "greennode/vks_mcp_server/templates"
```

(This affects wheel builds only; editable `uv run` loads templates via a path relative to `__file__`, so test runs are unaffected.)

- [ ] **Step 4: Verify both templates are valid YAML with placeholders intact**

Run from repo root:

```bash
cd src/vks-mcp-server && python -c "
import yaml
for f in ('deployment.yaml','service.yaml'):
    p = f'greennode/vks_mcp_server/templates/k8s-templates/{f}'
    txt = open(p).read()
    yaml.safe_load(txt)  # parses (placeholders are valid scalar tokens)
    assert 'APP_NAME' in txt
    print(f, 'OK')
print('vks.vngcloud.vn/scheme present:', 'vks.vngcloud.vn/scheme' in open('greennode/vks_mcp_server/templates/k8s-templates/service.yaml').read())
"
```
Expected: `deployment.yaml OK`, `service.yaml OK`, `vks.vngcloud.vn/scheme present: True`.

- [ ] **Step 5: Commit**

```bash
git add src/vks-mcp-server/greennode/vks_mcp_server/templates src/vks-mcp-server/pyproject.toml
git commit -m "feat(k8s): add Deployment/Service manifest templates for generate_app_manifest"
```

---

## Task 2: Implement `generate_app_manifest` + helpers (TDD)

**Files:**
- Create: `src/vks-mcp-server/tests/test_generate_app_manifest.py`
- Modify: `src/vks-mcp-server/greennode/vks_mcp_server/k8s_handler.py`

- [ ] **Step 1: Write the failing behavior tests**

Create `src/vks-mcp-server/tests/test_generate_app_manifest.py`:

```python
"""Tests for the generate_app_manifest tool."""
from __future__ import annotations

import pytest
import yaml
from mcp.server.fastmcp import FastMCP

from greennode.vks_mcp_server.auth import TokenManager
from greennode.vks_mcp_server.client import VksClient
from greennode.vks_mcp_server.config import load_config
from greennode.vks_mcp_server.k8s_handler import K8sHandler


@pytest.fixture
def handler_factory(sample_config):
    config = load_config(sample_config)
    client = VksClient(config, TokenManager(config))

    def make(allow_write: bool) -> K8sHandler:
        return K8sHandler(FastMCP("test"), config, client, allow_write=allow_write)

    return make


@pytest.mark.asyncio
async def test_requires_write_access(handler_factory, tmp_path):
    h = handler_factory(allow_write=False)
    with pytest.raises(RuntimeError, match="allow-write"):
        await h.generate_app_manifest(
            app_name="web", image_uri="img:1", output_dir=str(tmp_path)
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_requires_absolute_output_dir(handler_factory):
    h = handler_factory(allow_write=True)
    with pytest.raises(RuntimeError, match="absolute"):
        await h.generate_app_manifest(
            app_name="web", image_uri="img:1", output_dir="relative/dir"
        )


@pytest.mark.asyncio
async def test_rejects_invalid_app_name(handler_factory, tmp_path):
    h = handler_factory(allow_write=True)
    with pytest.raises(ValueError):
        await h.generate_app_manifest(
            app_name="Bad_Name", image_uri="img:1", output_dir=str(tmp_path)
        )


@pytest.mark.asyncio
async def test_happy_path_writes_manifest(handler_factory, tmp_path):
    h = handler_factory(allow_write=True)
    result = await h.generate_app_manifest(
        app_name="web",
        image_uri="vcr.vngcloud.vn/demo/web:1.0",
        output_dir=str(tmp_path),
        port=8080,
        replicas=3,
        cpu="100m",
        memory="128Mi",
        namespace="default",
        load_balancer_scheme="internal",
    )
    out = tmp_path / "web-manifest.yaml"
    assert out.exists()
    text = out.read_text()
    assert "vcr.vngcloud.vn/demo/web:1.0" in text
    assert "vks.vngcloud.vn/scheme: internal" in text
    assert "type: LoadBalancer" in text

    docs = list(yaml.safe_load_all(text))
    assert len(docs) == 2
    assert {d["kind"] for d in docs} == {"Deployment", "Service"}
    dep = next(d for d in docs if d["kind"] == "Deployment")
    assert dep["spec"]["replicas"] == 3
    assert dep["spec"]["template"]["spec"]["containers"][0]["ports"][0]["containerPort"] == 8080
    assert "web-manifest.yaml" in result  # markdown result mentions the saved path
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd src/vks-mcp-server && uv run pytest tests/test_generate_app_manifest.py -v`
Expected: FAIL — `AttributeError: 'K8sHandler' object has no attribute 'generate_app_manifest'`.

- [ ] **Step 3: Add `import re` to k8s_handler.py**

In `src/vks-mcp-server/greennode/vks_mcp_server/k8s_handler.py`, the current imports are:

```python
import json
import logging
import os

import yaml
from pydantic import Field
from typing import Any, Dict, Literal, Optional
```

Add `import re` so the block becomes:

```python
import json
import logging
import os
import re

import yaml
from pydantic import Field
from typing import Any, Dict, Literal, Optional
```

- [ ] **Step 4: Register the tool in `K8sHandler.__init__`**

In `K8sHandler.__init__`, after the existing line:

```python
        self.mcp.tool(name="apply_yaml")(self.apply_yaml)
```
add:
```python
        self.mcp.tool(name="generate_app_manifest")(self.generate_app_manifest)
```

- [ ] **Step 5: Add the helper methods and the tool**

In `src/vks-mcp-server/greennode/vks_mcp_server/k8s_handler.py`, add these three methods to the `K8sHandler` class (place them just after `cleanup_resource_response`, before `list_k8s_resources`):

```python
    @staticmethod
    def _validate_app_name(app_name: str) -> None:
        """Validate app_name against Kubernetes RFC 1123 DNS-label rules.

        Raises ValueError if invalid. Also prevents path traversal / injection.
        """
        if len(app_name) > 63:
            raise ValueError(
                f'Invalid app_name "{app_name}": must be at most 63 characters long'
            )
        if not re.match(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$", app_name):
            raise ValueError(
                f'Invalid app_name "{app_name}": must consist of lowercase '
                "alphanumeric characters or hyphens, and start and end with an "
                "alphanumeric character"
            )

    def _load_yaml_template(self, template_files: list[str], values: Dict[str, str]) -> str:
        """Load template files, substitute placeholders, and join with '---'."""
        templates_dir = os.path.join(os.path.dirname(__file__), "templates", "k8s-templates")
        contents = []
        for template_file in template_files:
            with open(os.path.join(templates_dir, template_file)) as f:
                content = f.read()
            for key, value in values.items():
                content = content.replace(key, value)
            contents.append(content)
        return "\n---\n".join(contents)

    async def generate_app_manifest(
        self,
        app_name: str = Field(
            ..., description="Application name; used for Deployment/Service names and labels."
        ),
        image_uri: str = Field(
            ...,
            description="Full container image URI with tag, e.g. 'vcr.vngcloud.vn/<repo>:<tag>'.",
        ),
        output_dir: str = Field(
            ..., description="Absolute path to the directory to save the manifest file."
        ),
        port: int = Field(
            80, ge=1, le=65535, description="Container/Service port the application listens on."
        ),
        replicas: int = Field(2, ge=1, description="Number of replicas to deploy."),
        cpu: str = Field(
            "100m", description="CPU request/limit per container, e.g. '100m', '500m'."
        ),
        memory: str = Field(
            "128Mi", description="Memory request/limit per container, e.g. '128Mi', '1Gi'."
        ),
        namespace: str = Field("default", description="Kubernetes namespace to deploy to."),
        load_balancer_scheme: Literal["internet-facing", "internal"] = Field(
            "internal",
            description="VKS LoadBalancer scheme, rendered as the vks.vngcloud.vn/scheme "
            "annotation. 'internal' = private VPC only; 'internet-facing' = public.",
        ),
    ) -> str:
        """Generate a Kubernetes Deployment + LoadBalancer Service manifest for an app.

        Writes `<app_name>-manifest.yaml` to output_dir and returns the YAML, ready to
        deploy with the apply_yaml tool. Use this instead of hand-writing manifests.

        ## Requirements
        - The server must be run with the `--allow-write` flag
        - output_dir must be an absolute path

        ## Generated resources
        - Deployment: manages the app pods (replicas, resource requests/limits)
        - Service: type LoadBalancer, exposed via the VKS LoadBalancer Controller
          (vks.vngcloud.vn/scheme annotation controls internal vs internet-facing)

        ## Workflow
        1. generate_app_manifest  -> creates the YAML file
        2. (review/edit the file if needed)
        3. apply_yaml             -> applies it to the cluster
        """
        if not self.allow_write:
            raise RuntimeError(
                "Write access denied: generate_app_manifest requires --allow-write flag."
            )
        if not os.path.isabs(output_dir):
            raise RuntimeError(f"Path must be absolute: {output_dir}")
        self._validate_app_name(app_name)

        template_values = {
            "APP_NAME": app_name,
            "NAMESPACE": namespace,
            "REPLICAS": str(replicas),
            "IMAGE_URI": image_uri,
            "PORT": str(port),
            "CPU": cpu,
            "MEMORY": memory,
            "LOAD_BALANCER_SCHEME": load_balancer_scheme,
        }
        combined_yaml = self._load_yaml_template(
            ["deployment.yaml", "service.yaml"], template_values
        )

        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.abspath(os.path.join(output_dir, f"{app_name}-manifest.yaml"))
        with open(output_file_path, "w") as f:
            f.write(combined_yaml)

        logger.info("Generated manifest for %s at %s", app_name, output_file_path)
        return (
            f"Successfully generated manifest for **{app_name}** "
            f"(image `{image_uri}`) and saved to `{output_file_path}`.\n\n"
            f"```yaml\n{combined_yaml}\n```"
        )
```

- [ ] **Step 6: Run the behavior tests to verify they pass**

Run: `cd src/vks-mcp-server && uv run pytest tests/test_generate_app_manifest.py -v`
Expected: PASS (4 tests).

- [ ] **Step 7: Run the full suite to verify no regression**

Run: `cd src/vks-mcp-server && uv run pytest tests/ -q`
Expected: all PASS (55 = previous 51 + 4 new).

- [ ] **Step 8: Commit**

```bash
git add src/vks-mcp-server/greennode/vks_mcp_server/k8s_handler.py src/vks-mcp-server/tests/test_generate_app_manifest.py
git commit -m "feat(k8s): add generate_app_manifest tool (ported from eks-mcp-server)"
```

---

## Task 3: Schema assertions

**Files:**
- Modify: `src/vks-mcp-server/tests/test_tool_schemas.py`

- [ ] **Step 1: Add a schema test (will fail until the tool is registered — it is, after Task 2, so it should pass once written; write it and run)**

Append to `src/vks-mcp-server/tests/test_tool_schemas.py`:

```python
@pytest.mark.asyncio
async def test_generate_app_manifest_schema(config, client):
    schema = await _schema_for(
        lambda mcp: K8sHandler(
            mcp, config, client, allow_write=True, allow_sensitive_data_access=True
        ),
        "generate_app_manifest",
    )
    props = schema["properties"]
    assert set(props["load_balancer_scheme"]["enum"]) == {"internet-facing", "internal"}
    assert props["port"]["minimum"] == 1
    assert props["port"]["maximum"] == 65535
    assert props["replicas"]["minimum"] == 1
```

- [ ] **Step 2: Run the schema test**

Run: `cd src/vks-mcp-server && uv run pytest tests/test_tool_schemas.py -k generate_app_manifest -v`
Expected: PASS.

- [ ] **Step 3: Run the full suite**

Run: `cd src/vks-mcp-server && uv run pytest tests/ -q`
Expected: all PASS (56 = 55 + 1 new).

- [ ] **Step 4: Commit**

```bash
git add src/vks-mcp-server/tests/test_tool_schemas.py
git commit -m "test(k8s): assert generate_app_manifest schema (enum + numeric bounds)"
```

---

## Task 4: Documentation

**Files:**
- Modify: `CLAUDE.md` (root) — tool count and k8s tool list
- Modify: `src/vks-mcp-server/CHANGELOG.md`
- Modify: `src/vks-mcp-server/README.md` — add generate_app_manifest to the Kubernetes tools bullet

- [ ] **Step 1: Update CLAUDE.md tool count**

In `CLAUDE.md`, change the overview bullet from:

```markdown
- **27 tools** across 5 handlers: Auth, Cluster, NodeGroup, Version, K8s
```
to:
```markdown
- **28 tools** across 5 handlers: Auth, Cluster, NodeGroup, Version, K8s
```

Also, in the "Key files" table row for the k8s handler, update its tool count to include `generate_app_manifest` (k8s handler now has 7 tools). Find the row beginning `| `k8s_handler.py`` and change its count from 6 to 7 tools, appending `+ generate_app_manifest` to the description.

- [ ] **Step 2: Update CHANGELOG**

In `src/vks-mcp-server/CHANGELOG.md`, under `## [Unreleased]` → `### Added`, add:

```markdown
- `generate_app_manifest` tool: scaffolds a Deployment + LoadBalancer Service
  manifest (VKS `vks.vngcloud.vn/scheme` annotation) and writes it for `apply_yaml`.
```

- [ ] **Step 3: Update README k8s tools bullet**

In `src/vks-mcp-server/README.md`, find the Kubernetes bullet:

```markdown
- **Kubernetes** — list resources, manage a single resource (CRUD), apply YAML,
  pod logs, resource events, list API versions
```
and change it to:
```markdown
- **Kubernetes** — list resources, manage a single resource (CRUD), apply YAML,
  generate app manifest, pod logs, resource events, list API versions
```

- [ ] **Step 4: Run the full suite one last time**

Run: `cd src/vks-mcp-server && uv run pytest tests/ -q`
Expected: all PASS (56).

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md src/vks-mcp-server/CHANGELOG.md src/vks-mcp-server/README.md
git commit -m "docs: record generate_app_manifest tool"
```

---

## Notes for the implementer

- Line/anchor references describe current file content; if a snippet's "from" text does not match, locate the equivalent and adapt — do not guess.
- The behavior tests call the handler method directly, so they pass ALL parameters explicitly (Pydantic `Field` defaults are not resolved on a direct Python call — only FastMCP resolves them). This is intentional; the schema test (Task 3) covers the defaults/constraints.
- `str.replace` substitution is safe here because placeholders are unique UPPERCASE tokens and `app_name` is validated to lowercase-only, so no cross-substitution occurs.
