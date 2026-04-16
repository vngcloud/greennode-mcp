"""Tests for response formatting models."""
from __future__ import annotations


from greennode.vks_mcp_server.models import (
    format_cluster_table,
    format_nodegroup_table,
    format_cluster_detail,
    format_nodegroup_detail,
)


def test_format_cluster_table():
    """Single cluster item renders name, id, status, region, and footer."""
    items = [
        {
            "name": "my-cluster",
            "uid": "cluster-uid-12345",
            "status": "ACTIVE",
            "version": "1.28",
            "nodeCount": 3,
            "createdAt": "2024-01-15T10:00:00Z",
        }
    ]
    result = format_cluster_table(items, region="HCM-3")
    assert "my-cluster" in result
    assert "cluster-uid-12345" in result
    assert "ACTIVE" in result
    assert "HCM-3" in result
    assert "Total: 1 cluster" in result


def test_format_cluster_table_empty():
    """Empty list returns 'No clusters found' message."""
    result = format_cluster_table([], region="HAN")
    assert "No clusters found" in result


def test_format_nodegroup_table():
    """Single node group item renders name, id, and cluster_name."""
    items = [
        {
            "name": "my-nodegroup",
            "uid": "ng-uid-67890",
            "status": "ACTIVE",
            "nodeCount": 2,
            "imageId": "img-abc123",
            "createdAt": "2024-02-01T08:00:00Z",
        }
    ]
    result = format_nodegroup_table(items, cluster_name="my-cluster")
    assert "my-nodegroup" in result
    assert "ng-uid-67890" in result
    assert "my-cluster" in result


def test_format_cluster_detail():
    """Full cluster dict renders id, networkType, and vpcId."""
    cluster = {
        "uid": "cluster-uid-abcdef",
        "name": "prod-cluster",
        "status": "ACTIVE",
        "version": "1.29",
        "networkType": "CALICO",
        "vpcId": "vpc-0011223344",
        "subnetId": "subnet-99887766",
        "cidr": "10.0.0.0/16",
        "nodeCount": 5,
        "privateCluster": False,
        "enabledAddons": {"lbPlugin": "true", "csiPlugin": "true"},
        "createdAt": "2024-03-10T12:00:00Z",
        "updatedAt": "2024-03-11T09:30:00Z",
    }
    result = format_cluster_detail(cluster)
    assert "cluster-uid-abcdef" in result
    assert "CALICO" in result
    assert "vpc-0011223344" in result


def test_format_nodegroup_detail():
    """Full node group dict with upgradeConfig, labels, taints, securityGroups renders correctly."""
    nodegroup = {
        "uid": "ng-uid-full-001",
        "clusterId": "cluster-uid-abcdef",
        "name": "worker-pool",
        "status": "ACTIVE",
        "nodeCount": 3,
        "imageId": "img-ubuntu-2204",
        "flavorId": "flv-4cpu-8gb",
        "disk": {"size": 50, "type": "SSD"},
        "privateNodes": True,
        "sshKeyId": "ssh-key-xyz",
        "securityGroups": ["sg-aabbccdd", "sg-11223344"],
        "upgradeConfig": {"strategy": "SURGE", "maxSurge": 1, "maxUnavailable": 0},
        "autoScaleConfig": {"minSize": 1, "maxSize": 5},
        "labels": {"env": "prod", "team": "platform"},
        "taints": [{"key": "dedicated", "value": "gpu", "effect": "NoSchedule"}],
        "createdAt": "2024-04-01T06:00:00Z",
        "updatedAt": "2024-04-02T07:15:00Z",
    }
    result = format_nodegroup_detail(nodegroup)
    assert "ng-uid-full-001" in result
    assert "worker-pool" in result
    assert "SSD" in result
    assert "SURGE" in result
