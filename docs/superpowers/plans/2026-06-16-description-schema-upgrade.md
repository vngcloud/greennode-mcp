# Description & Schema Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve tool descriptions and parameter schemas across all 27 greennode-mcp tools so the LLM selects and calls tools more accurately.

**Architecture:** Edit handler method signatures (add `Literal` and `Field(ge=/le=)` constraints) and docstrings/`body` descriptions. No execution-logic, transport, or auth changes. Schema constraints are verified by introspecting each registered tool's `inputSchema` via `FastMCP.list_tools()`, because the existing tests call internal functions directly and bypass FastMCP validation.

**Tech Stack:** Python, FastMCP (mcp 1.27.0), Pydantic v2, pytest + pytest-asyncio + respx.

**Spec:** `docs/superpowers/specs/2026-06-16-description-schema-upgrade-design.md`

---

## File structure

- Create: `tests/test_tool_schemas.py` — introspects registered tool input schemas (cross-cutting concern: schema correctness for all handlers).
- Modify: `src/vks_mcp_server/k8s_handler.py` — `operation` Literal; `get_pod_logs` numeric constraints.
- Modify: `src/vks_mcp_server/cluster_handler.py` — pagination constraints; enriched `body` descriptions; structured docstrings.
- Modify: `src/vks_mcp_server/nodegroup_handler.py` — pagination constraints; enriched `body` descriptions; structured docstrings.
- Modify: `src/vks_mcp_server/version_handler.py` — workflow hints in docstrings.
- Modify: `CLAUDE.md`, `README.md` (if present), changelog — per documentation rule.

Confirmed enum values (from code / shared greennode-cli): `networkType` = CALICO|CILIUM_OVERLAY|CILIUM_NATIVE_ROUTING; `releaseChannel` = RAPID|STABLE (default STABLE); k8s `operation` = create|replace|patch|delete|read. `diskType` values are NOT enumerated anywhere → description only.

---

## Task 1: Schema-test infrastructure + k8s_handler constraints

**Files:**
- Create: `tests/test_tool_schemas.py`
- Modify: `src/vks_mcp_server/k8s_handler.py` (imports; `manage_k8s_resource` signature line 375; `get_pod_logs` signature lines 204-206)

- [ ] **Step 1: Write the schema-introspection test file (will fail)**

Create `tests/test_tool_schemas.py`:

```python
"""Tests for registered tool input schemas via FastMCP introspection.

The existing handler tests call internal functions directly and bypass FastMCP
validation, so Literal / Field(ge,le) constraints are only observable on the
registered tool's inputSchema. These tests assert those constraints.
"""
from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP

from vks_mcp_server.auth import TokenManager
from vks_mcp_server.client import VksClient
from vks_mcp_server.config import load_config
from vks_mcp_server.cluster_handler import ClusterHandler
from vks_mcp_server.k8s_handler import K8sHandler
from vks_mcp_server.nodegroup_handler import NodeGroupHandler


@pytest.fixture
def config(sample_config):
    return load_config(sample_config)


@pytest.fixture
def client(config):
    return VksClient(config, TokenManager(config))


async def _schema_for(register, tool_name):
    """Register handler(s) on a fresh FastMCP and return a tool's inputSchema."""
    mcp = FastMCP("test")
    register(mcp)
    tools = await mcp.list_tools()
    return next(t for t in tools if t.name == tool_name).inputSchema


def _minimum(prop):
    """Extract the numeric 'minimum' whether top-level or inside anyOf (Optional)."""
    if "minimum" in prop:
        return prop["minimum"]
    for sub in prop.get("anyOf", []):
        if "minimum" in sub:
            return sub["minimum"]
    return None


@pytest.mark.asyncio
async def test_manage_k8s_resource_operation_is_enum(config, client):
    schema = await _schema_for(
        lambda mcp: K8sHandler(
            mcp, config, client, allow_write=True, allow_sensitive_data_access=True
        ),
        "manage_k8s_resource",
    )
    enum = schema["properties"]["operation"]["enum"]
    assert set(enum) == {"create", "replace", "patch", "delete", "read"}


@pytest.mark.asyncio
async def test_get_pod_logs_numeric_constraints(config, client):
    schema = await _schema_for(
        lambda mcp: K8sHandler(
            mcp, config, client, allow_write=True, allow_sensitive_data_access=True
        ),
        "get_pod_logs",
    )
    props = schema["properties"]
    assert props["tail_lines"]["minimum"] == 1
    assert props["limit_bytes"]["minimum"] == 1
    assert _minimum(props["since_seconds"]) == 0
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run python -m pytest tests/test_tool_schemas.py -v`
Expected: FAIL — `test_manage_k8s_resource_operation_is_enum` raises `KeyError: 'enum'` (operation is a plain string); `test_get_pod_logs_numeric_constraints` fails because no `minimum` exists yet.

- [ ] **Step 3: Add `Literal` to `operation` in k8s_handler.py**

In `src/vks_mcp_server/k8s_handler.py`, change the import line 10 from:

```python
from typing import Any, Dict, Optional
```
to:
```python
from typing import Any, Dict, Literal, Optional
```

Then change the `manage_k8s_resource` `operation` parameter (line 375) from:

```python
        operation: str = Field(..., description="Operation to perform on the resource. Valid values:\n            - create: Create a new resource\n            - replace: Replace an existing resource\n            - patch: Update specific fields of an existing resource\n            - delete: Delete an existing resource\n            - read: Get details of an existing resource\n            Use list_k8s_resources for listing multiple resources."),
```
to:
```python
        operation: Literal["create", "replace", "patch", "delete", "read"] = Field(..., description="Operation to perform on the resource:\n            - create: Create a new resource\n            - replace: Replace an existing resource\n            - patch: Update specific fields of an existing resource\n            - delete: Delete an existing resource\n            - read: Get details of an existing resource\n            Use list_k8s_resources for listing multiple resources."),
```

(The existing `Operation(operation)` call at line 415 still works: the Literal values equal the enum values.)

- [ ] **Step 4: Add numeric constraints to `get_pod_logs` in k8s_handler.py**

Change lines 203-205 from:

```python
        since_seconds: Optional[int] = Field(None, description="Only return logs newer than this many seconds. Useful for getting recent logs without retrieving the entire history."),
        tail_lines: int = Field(100, description="Number of lines to return from the end of the logs. Default: 100. Use higher values for more context."),
        limit_bytes: int = Field(10240, description="Maximum number of bytes to return. Default: 10KB (10240 bytes). Prevents retrieving extremely large log files."),
```
to:
```python
        since_seconds: Optional[int] = Field(None, ge=0, description="Only return logs newer than this many seconds. Useful for getting recent logs without retrieving the entire history."),
        tail_lines: int = Field(100, ge=1, description="Number of lines to return from the end of the logs. Default: 100. Use higher values for more context."),
        limit_bytes: int = Field(10240, ge=1, description="Maximum number of bytes to return. Default: 10KB (10240 bytes). Prevents retrieving extremely large log files."),
```

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `uv run python -m pytest tests/test_tool_schemas.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Run the full suite to verify no regression**

Run: `uv run python -m pytest tests/ -v`
Expected: all tests PASS (existing 44 + 2 new).

- [ ] **Step 7: Commit**

```bash
git add tests/test_tool_schemas.py src/vks_mcp_server/k8s_handler.py
git commit -m "feat(k8s): Literal operation + numeric constraints on get_pod_logs"
```

---

## Task 2: cluster_handler — pagination, body descriptions, docstrings

**Files:**
- Modify: `src/vks_mcp_server/cluster_handler.py` (`cluster_list` lines 344-345; `cluster_get_events` lines 422-423; `cluster_create` lines 368-375; `cluster_update` lines 384-388)
- Test: `tests/test_tool_schemas.py`

- [ ] **Step 1: Add schema tests for cluster pagination + body description (will fail)**

Append to `tests/test_tool_schemas.py`:

```python
@pytest.mark.asyncio
async def test_cluster_list_pagination_constraints(config, client):
    schema = await _schema_for(
        lambda mcp: ClusterHandler(mcp, config, client, allow_write=True),
        "cluster_list",
    )
    props = schema["properties"]
    assert _minimum(props["page"]) == 0
    assert _minimum(props["pageSize"]) == 1


@pytest.mark.asyncio
async def test_cluster_create_body_lists_valid_values(config, client):
    schema = await _schema_for(
        lambda mcp: ClusterHandler(mcp, config, client, allow_write=True),
        "cluster_create",
    )
    desc = schema["properties"]["body"]["description"]
    assert "RAPID" in desc and "STABLE" in desc
    assert "CILIUM_NATIVE_ROUTING" in desc
    assert "secondarySubnets" in desc
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run python -m pytest tests/test_tool_schemas.py -k cluster -v`
Expected: FAIL — `page`/`pageSize` have no minimum; `body` description lacks "RAPID"/"CILIUM_NATIVE_ROUTING"/"secondarySubnets".

- [ ] **Step 3: Add pagination constraints to `cluster_list`**

In `src/vks_mcp_server/cluster_handler.py`, change `cluster_list` parameters (lines 344-345) from:

```python
        page: int | None = Field(None, description="Page number (starts at 0)"),
        pageSize: int | None = Field(None, description="Number of clusters per page (default 50)"),
```
to:
```python
        page: int | None = Field(None, ge=0, description="Page number (starts at 0)"),
        pageSize: int | None = Field(None, ge=1, description="Number of clusters per page (default 50)"),
```

- [ ] **Step 4: Add pagination constraints to `cluster_get_events`**

Change `cluster_get_events` parameters (lines 422-423) from:

```python
        page: int | None = Field(None, description="Page number (starts at 0)"),
        pageSize: int | None = Field(None, description="Items per page (default 20)"),
```
to:
```python
        page: int | None = Field(None, ge=0, description="Page number (starts at 0)"),
        pageSize: int | None = Field(None, ge=1, description="Items per page (default 20)"),
```

- [ ] **Step 5: Enrich `cluster_create` body description + docstring**

Change the `cluster_create` `body` parameter (line 370) from:

```python
        body: dict = Field(..., description="CreateClusterComboDto body. Must include: name, releaseChannel, version, enablePrivateCluster, networkType, vpcId, subnetId, nodeGroups. Use cluster_create_validate first to check."),
```
to:
```python
        body: dict = Field(..., description=(
            "CreateClusterComboDto body (JSON object). Required top-level fields: "
            "name, releaseChannel, version, networkType, vpcId, subnetId, nodeGroups. "
            "Valid values - releaseChannel: RAPID | STABLE (default STABLE); "
            "networkType: CALICO | CILIUM_OVERLAY | CILIUM_NATIVE_ROUTING. "
            "Conditional: networkType CALICO or CILIUM_OVERLAY requires 'cidr'; "
            "CILIUM_NATIVE_ROUTING requires 'secondarySubnets'. "
            "Each nodeGroups[] item needs: name, imageId, flavorId, diskSize (20-5000), "
            "diskType, numNodes (0-10), securityGroups, sshKeyId, upgradeConfig. "
            "Call cluster_create_validate first to check the body."
        )),
```

Change the `cluster_create` docstring (line 375) from:

```python
        """Creates a new VKS cluster. Requires --allow-write flag. Use cluster_create_validate first to check the body."""
```
to:
```python
        """Create a new VKS cluster.

        ## Requirements
        - Server must run with --allow-write
        - Call cluster_create_validate first; fix any reported errors before creating

        ## Workflow
        1. cluster_versions_list   -> choose version / releaseChannel
        2. cluster_create_validate -> confirm the body is valid
        3. cluster_create
        """
```

- [ ] **Step 6: Enrich `cluster_update` body description + add structured docstring**

Change the `cluster_update` `body` parameter (line 385) from:

```python
        body: dict = Field(..., description="Fields to update (partial update supported)"),
```
to:
```python
        body: dict = Field(..., description=(
            "Fields to update as a JSON object (partial update supported). "
            "Provide only the top-level cluster fields you want to change. "
            "Use cluster_get first to see current values."
        )),
```

Change the `cluster_update` docstring (line 388) from:

```python
        """Updates an existing VKS cluster. Requires --allow-write flag."""
```
to:
```python
        """Update an existing VKS cluster (partial update supported).

        ## Requirements
        - Server must run with --allow-write
        """
```

- [ ] **Step 7: Run cluster schema tests to verify pass**

Run: `uv run python -m pytest tests/test_tool_schemas.py -k cluster -v`
Expected: PASS.

- [ ] **Step 8: Run full suite to verify no regression**

Run: `uv run python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add tests/test_tool_schemas.py src/vks_mcp_server/cluster_handler.py
git commit -m "feat(cluster): pagination constraints, richer body docs and docstrings"
```

---

## Task 3: nodegroup_handler — pagination, body descriptions, docstrings

**Files:**
- Modify: `src/vks_mcp_server/nodegroup_handler.py` (`nodegroup_create` lines 129-133; `nodegroup_update` line 146; `nodegroup_list_nodes` lines 183-184)
- Test: `tests/test_tool_schemas.py`

- [ ] **Step 1: Add schema tests for nodegroup (will fail)**

Append to `tests/test_tool_schemas.py`:

```python
@pytest.mark.asyncio
async def test_nodegroup_list_nodes_pagination_constraints(config, client):
    schema = await _schema_for(
        lambda mcp: NodeGroupHandler(mcp, config, client, allow_write=True),
        "nodegroup_list_nodes",
    )
    props = schema["properties"]
    assert _minimum(props["page"]) == 0
    assert _minimum(props["pageSize"]) == 1


@pytest.mark.asyncio
async def test_nodegroup_create_body_documents_ranges(config, client):
    schema = await _schema_for(
        lambda mcp: NodeGroupHandler(mcp, config, client, allow_write=True),
        "nodegroup_create",
    )
    desc = schema["properties"]["body"]["description"]
    assert "20-5000" in desc
    assert "0-10" in desc
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run python -m pytest tests/test_tool_schemas.py -k nodegroup -v`
Expected: FAIL — no minimum on page/pageSize; body description lacks ranges.

- [ ] **Step 3: Add pagination constraints to `nodegroup_list_nodes`**

In `src/vks_mcp_server/nodegroup_handler.py`, change lines 183-184 from:

```python
        page: int | None = Field(None, description="Page number (starts at 0)"),
        pageSize: int | None = Field(None, description="Items per page (default 50)"),
```
to:
```python
        page: int | None = Field(None, ge=0, description="Page number (starts at 0)"),
        pageSize: int | None = Field(None, ge=1, description="Items per page (default 50)"),
```

- [ ] **Step 4: Enrich `nodegroup_create` body description + docstring**

Change the `nodegroup_create` `body` parameter (line 130) from:

```python
        body: dict = Field(..., description="CreateNodeGroupDto body. Required fields: name, numNodes, imageId, flavorId, diskSize, diskType, enablePrivateNodes, securityGroups, sshKeyId, upgradeConfig"),
```
to:
```python
        body: dict = Field(..., description=(
            "CreateNodeGroupDto body (JSON object). Required fields: name, "
            "numNodes (0-10), imageId, flavorId, diskSize (20-5000), diskType, "
            "enablePrivateNodes, securityGroups, sshKeyId, upgradeConfig. "
            "Use nodegroup_images_list to find a valid imageId."
        )),
```

Change the `nodegroup_create` docstring (line 133) from:

```python
        """Creates a new node group in a VKS cluster. Requires --allow-write flag."""
```
to:
```python
        """Create a new node group in a VKS cluster.

        ## Requirements
        - Server must run with --allow-write

        ## Workflow
        1. nodegroup_images_list -> choose imageId
        2. nodegroup_create
        """
```

- [ ] **Step 5: Enrich `nodegroup_update` body description**

Change the `nodegroup_update` `body` parameter (line 146) from:

```python
        body: dict = Field(..., description="Update body. 'imageId' is REQUIRED. Optional: numNodes, securityGroups, labels, taints, autoScaleConfig, upgradeConfig"),
```
to:
```python
        body: dict = Field(..., description=(
            "Update body (JSON object). 'imageId' is REQUIRED. Optional: "
            "numNodes (0-10), securityGroups, labels, taints, autoScaleConfig, "
            "upgradeConfig."
        )),
```

- [ ] **Step 6: Run nodegroup schema tests to verify pass**

Run: `uv run python -m pytest tests/test_tool_schemas.py -k nodegroup -v`
Expected: PASS.

- [ ] **Step 7: Run full suite to verify no regression**

Run: `uv run python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add tests/test_tool_schemas.py src/vks_mcp_server/nodegroup_handler.py
git commit -m "feat(nodegroup): pagination constraints, richer body docs and docstrings"
```

---

## Task 4: version_handler — workflow hints in docstrings

**Files:**
- Modify: `src/vks_mcp_server/version_handler.py` (`cluster_versions_list` line 101; `nodegroup_images_list` line 109)
- Test: `tests/test_tool_schemas.py`

No schema constraints here (both tools take only `region`). These are read-only discovery tools; the useful upgrade is telling the LLM when to call them. auth_handler's `get_access_token` is already adequately described and is left unchanged. The tool docstring is exposed as `tool.description` (NOT inside `inputSchema`), so this task reads it directly.

- [ ] **Step 1: Add a docstring-presence test (will fail)**

Append to `tests/test_tool_schemas.py`:

```python
from vks_mcp_server.version_handler import VersionHandler


async def _description_for(register, tool_name):
    """Register handler(s) on a fresh FastMCP and return a tool's description (docstring)."""
    mcp = FastMCP("test")
    register(mcp)
    tools = await mcp.list_tools()
    return next(t for t in tools if t.name == tool_name).description


@pytest.mark.asyncio
async def test_version_tools_have_workflow_hints(config, client):
    cv = await _description_for(
        lambda mcp: VersionHandler(mcp, config, client), "cluster_versions_list"
    )
    ng = await _description_for(
        lambda mcp: VersionHandler(mcp, config, client), "nodegroup_images_list"
    )
    assert "cluster_create" in cv
    assert "nodegroup_create" in ng
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run python -m pytest tests/test_tool_schemas.py -k version -v`
Expected: FAIL — descriptions do not yet mention `cluster_create` / `nodegroup_create`.

- [ ] **Step 3: Add workflow hint to `cluster_versions_list`**

In `src/vks_mcp_server/version_handler.py`, change the `cluster_versions_list` docstring (line 101) from:

```python
        """Lists available Kubernetes versions for VKS clusters. Only shows enabled versions. Marks the latest stable non-deprecated version as recommended."""
```
to:
```python
        """List available Kubernetes versions for VKS clusters.

        Only shows enabled versions and marks the latest stable non-deprecated
        version as recommended. Call this before cluster_create to choose a
        valid version and releaseChannel.
        """
```

- [ ] **Step 4: Add workflow hint to `nodegroup_images_list`**

Change the `nodegroup_images_list` docstring (line 109) from:

```python
        """Lists available node group images for VKS. Only shows enabled images with OS, ID, Kubernetes version, and stage."""
```
to:
```python
        """List available node group images for VKS.

        Only shows enabled images with OS, ID, Kubernetes version, and stage.
        Call this before nodegroup_create to choose a valid imageId.
        """
```

- [ ] **Step 5: Run version tests to verify pass**

Run: `uv run python -m pytest tests/test_tool_schemas.py -k version -v`
Expected: PASS.

- [ ] **Step 6: Run full suite to verify no regression**

Run: `uv run python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/test_tool_schemas.py src/vks_mcp_server/version_handler.py
git commit -m "feat(version): add workflow hints to version/image listing tools"
```

---

## Task 5: Documentation update + final regression

**Files:**
- Modify: `CLAUDE.md` (and `README.md` if present in the working tree)
- Test: full suite

- [ ] **Step 1: Update CLAUDE.md "Adding a new tool" / conventions note**

In `CLAUDE.md`, under the "Adding a new tool" section, add a bullet after the existing list documenting the new conventions (find the numbered list ending at "Add tests in `tests/`" and append):

```markdown
8. Use `Literal[...]` for parameters with a fixed value set, and `Field(ge=, le=)` for numeric bounds, so the schema is self-documenting
9. For `body: dict` params, list required fields, valid values, and conditional logic in the Field description
10. Write structured docstrings (`## Requirements`, `## Workflow`) for create/update/delete tools
```

- [ ] **Step 2: Add a changelog entry**

If a changelog file exists (e.g. `CHANGELOG.md` or a `.changes/` entry per the repo's tooling), add:

```markdown
- Improved tool descriptions and schemas: Literal/enum and numeric constraints,
  enriched body-parameter documentation, and structured docstrings across cluster,
  nodegroup, version, and k8s tools.
```

If no changelog mechanism is present in the current working tree, skip this step and note it in the commit message.

- [ ] **Step 3: Run the entire test suite one final time**

Run: `uv run python -m pytest tests/ -v`
Expected: all tests PASS (existing 44 + new schema tests).

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: record description/schema conventions and changelog entry"
```

---

## Notes for the implementer

- Line numbers reference the working-tree files as of plan authoring; if they have shifted, locate the exact `Field(...)`/docstring shown in the "from" block and replace it. The "from" blocks are exact current text.
- The working tree is mid-restructure: `src/vks_mcp_server/` and `tests/` are untracked relative to HEAD. Commit only the specific files listed in each task's `git add` — do NOT `git add -A` (it would sweep in the unrelated pending deletions/restructure).
- Run tests with `uv run python -m pytest` per CLAUDE.md.
