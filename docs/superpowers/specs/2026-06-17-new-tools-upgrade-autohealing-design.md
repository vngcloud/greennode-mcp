# Design: New tools — nodegroup_upgrade_version & cluster_auto_healing_config

Date: 2026-06-17

## Context

A coverage-gap analysis of the latest VKS OpenAPI spec
(`/Users/lap16104/Documents/vks/context/api-docs/vks.json`) found endpoints with
no MCP tool. Two were selected to implement now:

- `POST /v1/clusters/{clusterId}/node-groups/{nodeGroupId}/upgrade-version`
- `PATCH /v1/clusters/{clusterId}/auto-healing-config`

(Deferred: `GET /v1/quota`, `GET /v1/clusters/{id}/upgrade-insight`,
`GET .../node-groups/{ng}/events`.)

## Spec details (from vks.json)

- `UpgradeNodeGroupVersionDto` — required: `kubernetesVersion` (string).
- `ClusterAutoHealingConfigDto` — required: `enableAutoHealing` (boolean);
  optional: `maxUnhealthy` (string), `unhealthyRange` (string),
  `timeoutUnhealthy` (integer, 5–180), `remediationTimedOutEmitted` (boolean,
  internal — NOT exposed).

## Goal

Add two write tools and the `PATCH` client method they need, following the
existing handler conventions (markdown `str` return, raise on error, Field
descriptions, conditional registration under `--allow-write`).

## Non-goals

- No `remediationTimedOutEmitted` parameter (internal status flag).
- No client-side validation of `kubernetesVersion` against available versions
  (the API validates; the description points users at `cluster_versions_list`).
- Not implementing the deferred endpoints.

## Tool 1: nodegroup_upgrade_version (nodegroup_handler.py)

```python
async def nodegroup_upgrade_version(
    self,
    cluster_id: str = Field(..., description="VKS Cluster ID"),
    nodegroup_id: str = Field(..., description="Node Group ID to upgrade"),
    kubernetes_version: str = Field(
        ...,
        description="Target Kubernetes version. Use cluster_versions_list to see valid versions.",
    ),
    region: str | None = Field(None, description="Region override"),
) -> str:
```
- Registered only when `allow_write` (in `NodeGroupHandler.__init__` write block).
- `validate_id(cluster_id, "cluster_id")`, `validate_id(nodegroup_id, "nodegroup_id")`.
- `POST /v1/clusters/{cluster_id}/node-groups/{nodegroup_id}/upgrade-version`
  with JSON body `{"kubernetesVersion": kubernetes_version}`.
- Docstring: structured (`## Requirements` — needs `--allow-write`).
- Returns a markdown success string mentioning the nodegroup and target version.

## Tool 2: cluster_auto_healing_config (cluster_handler.py)

```python
async def cluster_auto_healing_config(
    self,
    cluster_id: str = Field(..., description="Cluster ID"),
    enable_auto_healing: bool = Field(..., description="Enable or disable auto-healing for the cluster"),
    max_unhealthy: str | None = Field(None, description="Max number or percentage of unhealthy nodes before remediation, e.g. '2' or '40%'"),
    unhealthy_range: str | None = Field(None, description="Range of unhealthy nodes allowed before remediation, e.g. '[3-5]'"),
    timeout_unhealthy: int | None = Field(None, ge=5, le=180, description="Minutes to wait before considering a node unhealthy (5-180)"),
    region: str | None = Field(None, description="Region override"),
) -> str:
```
- Registered only when `allow_write` (in `ClusterHandler.__init__` write block).
- `validate_id(cluster_id, "cluster_id")`.
- Body built with camelCase keys, including only provided (non-None) optionals:
  `enableAutoHealing` (always), `maxUnhealthy`, `unhealthyRange`, `timeoutUnhealthy`.
- `PATCH /v1/clusters/{cluster_id}/auto-healing-config`.
- Docstring: structured (`## Requirements` — needs `--allow-write`).
- Returns a markdown success string.

## Infrastructure: VksClient.patch

`VksClient` has get/post/put/delete/get_raw but no `patch`. Add:
```python
async def patch(self, path, region=None, params=None, json=None):
    return await self._request("PATCH", path, region=region, params=params, json=json)
```
`_request` already accepts an arbitrary method string, so PATCH flows through the
existing retry/401/timeout logic unchanged.

## Testing

`tests/test_nodegroup_tools.py` (or a dedicated file):
- `nodegroup_upgrade_version`: with respx, POST to the upgrade-version path is
  called with body `{"kubernetesVersion": "v1.29.0"}`; returns success text.
  Invalid cluster_id/nodegroup_id raises (validate_id).

`tests/test_cluster_tools.py`:
- `cluster_auto_healing_config`: PATCH called; body contains `enableAutoHealing`
  and only the provided optionals (e.g. omitting `max_unhealthy` keeps it out of
  the body); returns success text.

`tests/test_tool_schemas.py`:
- `cluster_auto_healing_config.timeout_unhealthy` has minimum 5 / maximum 180
  (build the handler with `allow_write=True`).
- Both new tools are registered only under `allow_write=True` (assert present
  when True; the existing conditional-registration pattern already governs this).

`tests/test_client.py`:
- `VksClient.patch` issues a PATCH (respx) and returns parsed JSON.

## Docs

- CLAUDE.md: tool count 27 → 29; bump cluster_handler row (+1) and
  nodegroup_handler row (+1) counts and descriptions.
- server.py SERVER_INSTRUCTIONS: add both tools under the Write section.
- README.md: add to Cluster and NodeGroup bullets.
- CHANGELOG.md: Added entries.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Inventing body fields | Use only spec fields (UpgradeNodeGroupVersionDto, ClusterAutoHealingConfigDto) |
| PATCH unsupported | Add VksClient.patch; _request already handles arbitrary methods |
| Sending None optionals | Build auto-healing body with only provided keys |
