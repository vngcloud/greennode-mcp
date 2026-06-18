"""Pydantic BaseModel classes for GreenNode MCP Server responses."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _date(dt: str | None) -> str:
    """Return the first 10 characters of a date string, or empty string."""
    if not dt:
        return ""
    return str(dt)[:10]


def _kv_table(data: list[tuple[str, str]]) -> str:
    """Render a list of (key, value) tuples as a markdown key-value table."""
    rows = ["| Property | Value |", "|---|---|"]
    for k, v in data:
        rows.append(f"| {k} | {v} |")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Cluster models
# ---------------------------------------------------------------------------


class ClusterSummary(BaseModel):
    """Summary of a VKS cluster, used in list responses."""

    id: str = Field(..., description="Cluster ID")
    name: str = Field("", description="Cluster name")
    status: str = Field("", description="Cluster status (ACTIVE, CREATING, DELETING, etc.)")
    version: str = Field("", description="Kubernetes version")
    num_nodes: int | str = Field(0, description="Number of nodes")
    created_at: str = Field("", description="Creation timestamp")

    @classmethod
    def from_api(cls, data: dict) -> ClusterSummary:
        """Build a ClusterSummary from a raw VKS API cluster dict."""
        return cls(
            id=data.get("uid", data.get("id", "")),
            name=data.get("name", ""),
            status=data.get("status", ""),
            version=data.get("version", data.get("kubernetesVersion", "")),
            num_nodes=data.get("nodeCount", data.get("numNodes", "")),
            created_at=data.get("createdAt", ""),
        )


class ClusterListData(BaseModel):
    """Wrapper for cluster list response."""

    region: str = Field(..., description="Region name")
    clusters: list[ClusterSummary] = Field(default_factory=list, description="List of clusters")

    @property
    def total(self) -> int:
        """Return the number of clusters in the list."""
        return len(self.clusters)

    def to_markdown(self) -> str:
        """Render the cluster list as a markdown table."""
        if not self.clusters:
            return f"No clusters found (region: {self.region})"
        rows = [
            f"Cluster list (region: {self.region}):",
            "| # | Name | ID | Status | Version | Node count | Created |",
            "|---|---|---|---|---|---|---|",
        ]
        for i, c in enumerate(self.clusters, start=1):
            rows.append(
                f"| {i} | {c.name} | {c.id} | {c.status} | {c.version} | {c.num_nodes} | {_date(c.created_at)} |"
            )
        rows.append(f"\nTotal: {len(self.clusters)} cluster(s)")
        return "\n".join(rows)


class ClusterDetail(BaseModel):
    """Full detail of a VKS cluster."""

    id: str = Field(..., description="Cluster ID")
    name: str = Field("", description="Cluster name")
    description: str = Field("", description="Cluster description")
    status: str = Field("", description="Cluster status")
    version: str = Field("", description="Kubernetes version")
    release_channel: str = Field("", description="Release channel (STABLE, RAPID)")
    network_type: str = Field("", description="Network type")
    vpc_id: str = Field("", description="VPC ID")
    subnet_id: str = Field("", description="Subnet ID")
    cidr: str = Field("", description="CIDR")
    az_strategy: str = Field("", description="Availability zone strategy")
    list_subnet_ids: list[str] = Field(default_factory=list, description="List of subnet IDs")
    secondary_subnets: list[str] = Field(default_factory=list, description="Secondary subnets")
    num_nodes: int | str = Field(0, description="Number of nodes")
    enable_private_cluster: str = Field("", description="Whether private cluster is enabled")
    enabled_lb_plugin: str = Field("", description="Load balancer plugin enabled")
    enabled_csi_plugin: str = Field("", description="CSI plugin enabled")
    enabled_service_endpoint: str = Field("", description="Service endpoint enabled")
    whitelist_node_cidrs: str = Field("", description="Whitelist node CIDRs")
    poc: str = Field("", description="Whether this is a PoC cluster")
    auto_renewal: str = Field("", description="Auto renewal enabled")
    auto_upgrade_config: Optional[dict] = Field(None, description="Auto-upgrade configuration")
    fleet: str = Field("", description="Fleet info")
    location: str = Field("", description="Location")
    created_at: str = Field("", description="Creation timestamp")
    updated_at: str = Field("", description="Last update timestamp")

    @classmethod
    def from_api(cls, c: dict) -> ClusterDetail:
        """Build a ClusterDetail from a raw VKS API cluster dict."""
        network_type = c.get("networkType", c.get("network", {}).get("type", ""))
        vpc_id = c.get("vpcId", "")
        subnet_id = c.get("subnetId", "")
        cidr = c.get("cidr", "")
        return cls(
            id=c.get("uid", c.get("id", "")),
            name=c.get("name", ""),
            description=c.get("description", ""),
            status=c.get("status", ""),
            version=c.get("version", c.get("kubernetesVersion", "")),
            release_channel=c.get("releaseChannel", ""),
            network_type=network_type,
            vpc_id=vpc_id,
            subnet_id=subnet_id,
            cidr=cidr,
            az_strategy=c.get("azStrategy", ""),
            list_subnet_ids=c.get("listSubnetIds", []),
            secondary_subnets=c.get("secondarySubnets", []),
            num_nodes=c.get("nodeCount", c.get("numNodes", "")),
            enable_private_cluster=str(c.get("enablePrivateCluster", "")),
            enabled_lb_plugin=str(c.get("enabledLoadBalancerPlugin", "")),
            enabled_csi_plugin=str(c.get("enabledBlockStoreCsiPlugin", "")),
            enabled_service_endpoint=str(c.get("enabledServiceEndpoint", "")),
            whitelist_node_cidrs=str(c.get("whitelistNodeCIDRs", "")),
            poc=str(c.get("poc", "")),
            auto_renewal=str(c.get("autoRenewal", "")),
            auto_upgrade_config=c.get("autoUpgradeConfig", None),
            fleet=str(c.get("fleet", "")),
            location=str(c.get("location", "")),
            created_at=c.get("createdAt", ""),
            updated_at=c.get("updatedAt", ""),
        )

    def to_markdown(self) -> str:
        """Render the cluster details as markdown."""
        if self.auto_upgrade_config:
            auto_upgrade = (
                f"{self.auto_upgrade_config.get('weekdays', '')}"
                f" at {self.auto_upgrade_config.get('time', '')}"
            )
        else:
            auto_upgrade = "(not configured)"

        if self.fleet:
            fleet = f"{self.fleet.get('name', '')} ({self.fleet.get('id', '')})"
        else:
            fleet = "(none)"

        whitelist = self.whitelist_node_cidrs if self.whitelist_node_cidrs else ""
        secondary = ", ".join(self.secondary_subnets) if self.secondary_subnets else ""
        list_subnets = ", ".join(self.list_subnet_ids) if self.list_subnet_ids else ""

        data = [
            ("ID", self.id),
            ("Name", self.name),
            ("Description", self.description),
            ("Status", self.status),
            ("Version", self.version),
            ("Release Channel", self.release_channel),
            ("Network Type", self.network_type),
            ("VPC ID", self.vpc_id),
            ("Subnet ID", self.subnet_id),
            ("CIDR", self.cidr),
            ("AZ Strategy", self.az_strategy),
            ("List Subnet IDs", list_subnets),
            ("Secondary Subnets", secondary),
            ("Node count", str(self.num_nodes)),
            ("Private Cluster", self.enable_private_cluster),
            ("LB Plugin", self.enabled_lb_plugin),
            ("CSI Plugin", self.enabled_csi_plugin),
            ("Service Endpoint", self.enabled_service_endpoint),
            ("Whitelist Node CIDRs", whitelist),
            ("PoC", self.poc),
            ("Auto Renewal", self.auto_renewal),
            ("Auto-Upgrade", auto_upgrade),
            ("Fleet", fleet),
            ("Location", self.location),
            ("Created", _date(self.created_at)),
            ("Updated", _date(self.updated_at)),
        ]
        return f"Cluster detail **{self.name}**:\n" + _kv_table(data)


# ---------------------------------------------------------------------------
# Node group models
# ---------------------------------------------------------------------------


class NodeGroupSummary(BaseModel):
    """Summary of a VKS node group, used in list responses."""

    id: str = Field(..., description="Node group ID")
    name: str = Field("", description="Node group name")
    status: str = Field("", description="Node group status")
    num_nodes: int | str = Field(0, description="Number of nodes")
    image_id: str = Field("", description="Image ID")
    created_at: str = Field("", description="Creation timestamp")

    @classmethod
    def from_api(cls, data: dict) -> NodeGroupSummary:
        """Build a NodeGroupSummary from a raw VKS API node-group dict."""
        return cls(
            id=data.get("uid", data.get("id", "")),
            name=data.get("name", ""),
            status=data.get("status", ""),
            num_nodes=data.get("nodeCount", data.get("numNodes", "")),
            image_id=data.get("imageId", ""),
            created_at=data.get("createdAt", ""),
        )


class NodeGroupListData(BaseModel):
    """Wrapper for node group list response."""

    cluster_name: str = Field("", description="Parent cluster name")
    node_groups: list[NodeGroupSummary] = Field(
        default_factory=list, description="List of node groups"
    )

    @property
    def total(self) -> int:
        """Return the number of node groups in the list."""
        return len(self.node_groups)

    def to_markdown(self) -> str:
        """Render the node-group list as a markdown table."""
        if not self.node_groups:
            return f"No node groups found in cluster {self.cluster_name}"
        rows = [
            f"Node groups of cluster {self.cluster_name}:",
            "| # | Name | ID | Status | Node count | Image ID | Created |",
            "|---|---|---|---|---|---|---|",
        ]
        for i, ng in enumerate(self.node_groups, start=1):
            rows.append(
                f"| {i} | {ng.name} | {ng.id} | {ng.status} | {ng.num_nodes} | {ng.image_id} | {_date(ng.created_at)} |"
            )
        return "\n".join(rows)


class NodeGroupDetail(BaseModel):
    """Full detail of a VKS node group."""

    id: str = Field(..., description="Node group ID")
    cluster_id: str = Field("", description="Parent cluster ID")
    name: str = Field("", description="Node group name")
    status: str = Field("", description="Node group status")
    num_nodes: int | str = Field(0, description="Number of nodes")
    image_id: str = Field("", description="Image ID")
    flavor_id: str = Field("", description="Flavor ID")
    disk_size: str = Field("", description="Disk size")
    disk_type: str = Field("", description="Disk type")
    enable_private_nodes: str = Field("", description="Whether private nodes enabled")
    ssh_key_id: str = Field("", description="SSH key ID")
    security_groups: list[str] = Field(default_factory=list, description="Security group IDs")
    upgrade_config: Optional[dict] = Field(None, description="Upgrade configuration")
    auto_scale_config: Optional[dict] = Field(None, description="Auto-scale configuration")
    labels: dict[str, str] = Field(default_factory=dict, description="Node labels")
    taints: list[dict] = Field(default_factory=list, description="Node taints")
    created_at: str = Field("", description="Creation timestamp")
    updated_at: str = Field("", description="Last update timestamp")

    @classmethod
    def from_api(cls, ng: dict) -> NodeGroupDetail:
        """Build a NodeGroupDetail from a raw VKS API node-group dict."""
        disk_size = str(ng.get("disk", {}).get("size", ng.get("diskSize", "")))
        disk_type = ng.get("disk", {}).get("type", ng.get("diskType", ""))
        return cls(
            id=ng.get("uid", ng.get("id", "")),
            cluster_id=ng.get("clusterId", ng.get("clusterUid", "")),
            name=ng.get("name", ""),
            status=ng.get("status", ""),
            num_nodes=ng.get("nodeCount", ng.get("numNodes", "")),
            image_id=ng.get("imageId", ""),
            flavor_id=ng.get("flavorId", ng.get("flavor", "")),
            disk_size=disk_size,
            disk_type=disk_type,
            enable_private_nodes=str(ng.get("privateNodes", "")),
            ssh_key_id=ng.get("sshKeyId", ng.get("sshKey", "")),
            security_groups=ng.get("securityGroups", []),
            upgrade_config=ng.get("upgradeConfig", None),
            auto_scale_config=ng.get("autoScaleConfig", ng.get("autoscale", None)),
            labels=ng.get("labels", {}),
            taints=ng.get("taints", []),
            created_at=ng.get("createdAt", ""),
            updated_at=ng.get("updatedAt", ""),
        )

    def to_markdown(self) -> str:
        """Render the node-group details as markdown."""
        disk = (
            f"{self.disk_size} GB ({self.disk_type})" if self.disk_size and self.disk_type else ""
        )

        if self.upgrade_config:
            uc = self.upgrade_config
            upgrade = f"strategy={uc.get('strategy', '')}, maxSurge={uc.get('maxSurge', '')}, maxUnavailable={uc.get('maxUnavailable', '')}"
        else:
            upgrade = ""

        if self.auto_scale_config:
            asc = self.auto_scale_config
            autoscale = f"{asc.get('minSize', '')}-{asc.get('maxSize', '')}"
        else:
            autoscale = "not configured"

        labels = ", ".join(f"{k}={v}" for k, v in self.labels.items()) if self.labels else ""
        taints = (
            ", ".join(
                f"{t.get('key', '')}={t.get('value', '')}:{t.get('effect', '')}"
                for t in self.taints
            )
            if self.taints
            else ""
        )
        sgs = ", ".join(str(s) for s in self.security_groups) if self.security_groups else ""

        data = [
            ("ID", self.id),
            ("Cluster ID", self.cluster_id),
            ("Name", self.name),
            ("Status", self.status),
            ("Node count", str(self.num_nodes)),
            ("Image ID", self.image_id),
            ("Flavor ID", self.flavor_id),
            ("Disk", disk),
            ("Private Nodes", self.enable_private_nodes),
            ("SSH Key ID", self.ssh_key_id),
            ("Security Groups", sgs),
            ("Upgrade Config", upgrade),
            ("Auto-scale", autoscale),
            ("Labels", labels),
            ("Taints", taints),
            ("Created", _date(self.created_at)),
            ("Updated", _date(self.updated_at)),
        ]
        return f"Node group detail **{self.name}**:\n" + _kv_table(data)


# ---------------------------------------------------------------------------
# Format helpers (used by handlers)
# ---------------------------------------------------------------------------


def format_cluster_table(items: list[dict], region: str) -> str:
    """Format a list of clusters as a markdown table.

    Args:
        items: List of cluster dicts from the VKS API.
        region: The region name to display in the header.

    Returns:
        Markdown-formatted table string.
    """
    clusters = [ClusterSummary.from_api(c) for c in items]
    return ClusterListData(region=region, clusters=clusters).to_markdown()


def format_nodegroup_table(items: list[dict], cluster_name: str = "") -> str:
    """Format a list of node groups as a markdown table.

    Args:
        items: List of node group dicts from the VKS API.
        cluster_name: The name of the parent cluster.

    Returns:
        Markdown-formatted table string.
    """
    node_groups = [NodeGroupSummary.from_api(ng) for ng in items]
    return NodeGroupListData(cluster_name=cluster_name, node_groups=node_groups).to_markdown()


def format_cluster_detail(c: dict) -> str:
    """Format full cluster details as a markdown key-value table.

    Args:
        c: Cluster dict from the VKS API.

    Returns:
        Markdown-formatted detail string.
    """
    return ClusterDetail.from_api(c).to_markdown()


def format_nodegroup_detail(ng: dict) -> str:
    """Format full node group details as a markdown key-value table.

    Args:
        ng: Node group dict from the VKS API.

    Returns:
        Markdown-formatted detail string.
    """
    return NodeGroupDetail.from_api(ng).to_markdown()


# ---------------------------------------------------------------------------
# Kubernetes resource models
# ---------------------------------------------------------------------------


class Operation(str, Enum):
    """Kubernetes resource operations."""

    CREATE = "create"
    REPLACE = "replace"
    PATCH = "patch"
    DELETE = "delete"
    READ = "read"


class ResourceSummary(BaseModel):
    """Summary of a Kubernetes resource."""

    name: str = Field(..., description="Name of the resource")
    namespace: Optional[str] = Field(None, description="Namespace of the resource")
    creation_timestamp: Optional[str] = Field(None, description="Creation timestamp")
    labels: Optional[Dict[str, str]] = Field(None, description="Resource labels")
    annotations: Optional[Dict[str, str]] = Field(None, description="Resource annotations")


class KubernetesResourceListData(BaseModel):
    """Data model for list_k8s_resources response."""

    kind: str = Field(..., description="Kind of the Kubernetes resources")
    api_version: str = Field(..., description="API version")
    namespace: Optional[str] = Field(None, description="Namespace")
    count: int = Field(..., description="Number of resources found")
    items: List[ResourceSummary] = Field(..., description="List of resources")


class KubernetesResourceData(BaseModel):
    """Data model for manage_k8s_resource response."""

    kind: str = Field(..., description="Kind of the Kubernetes resource")
    name: str = Field(..., description="Name of the Kubernetes resource")
    namespace: Optional[str] = Field(None, description="Namespace")
    api_version: str = Field(..., description="API version")
    operation: str = Field(..., description="Operation performed")
    resource: Optional[Dict[str, Any]] = Field(None, description="Resource data (for read)")


class EventItem(BaseModel):
    """Summary of a Kubernetes event."""

    first_timestamp: Optional[str] = Field(None, description="First timestamp")
    last_timestamp: Optional[str] = Field(None, description="Last timestamp")
    count: Optional[int] = Field(0, description="Count of occurrences", ge=0)
    message: str = Field(..., description="Event message")
    reason: str = Field(..., description="Reason for the event")
    reporting_component: str = Field(..., description="Reporting component")
    type: str = Field(..., description="Event type (Normal, Warning)")


class EventsData(BaseModel):
    """Data model for get_k8s_events response."""

    involved_object_kind: str = Field(..., description="Kind of the involved object")
    involved_object_name: str = Field(..., description="Name of the involved object")
    involved_object_namespace: Optional[str] = Field(None, description="Namespace")
    count: int = Field(..., description="Number of events found")
    events: List[EventItem] = Field(..., description="List of events")


class PodLogsData(BaseModel):
    """Data model for get_pod_logs response."""

    pod_name: str = Field(..., description="Name of the pod")
    namespace: str = Field(..., description="Namespace of the pod")
    container_name: Optional[str] = Field(None, description="Container name")
    log_lines: List[str] = Field(..., description="Pod log lines")


class ApplyYamlData(BaseModel):
    """Data model for apply_yaml response."""

    force_applied: bool = Field(False, description="Whether force was used")
    resources_created: int = Field(0, description="Number of resources created")
    resources_updated: int = Field(0, description="Number of resources updated")


class ApiVersionsData(BaseModel):
    """Data model for list_api_versions response."""

    cluster_id: str = Field(..., description="VKS Cluster ID")
    api_versions: List[str] = Field(..., description="Available API versions")
    count: int = Field(..., description="Number of API versions")
