"""Tests for _summarize_status — compact status one-liners per K8s kind."""
from __future__ import annotations

from greennode.greenode_mcp_server.k8s_handler import _summarize_status


def test_pod_running_ready():
    pod = {
        "status": {
            "phase": "Running",
            "containerStatuses": [
                {"ready": True, "restartCount": 0},
                {"ready": True, "restartCount": 2},
            ],
        }
    }
    assert _summarize_status("Pod", pod) == "Running (ready 2/2, restarts 2)"


def test_pod_pending_not_ready():
    pod = {
        "status": {
            "phase": "Pending",
            "containerStatuses": [{"ready": False, "restartCount": 0}],
        }
    }
    assert _summarize_status("Pod", pod) == "Pending (ready 0/1, restarts 0)"


def test_pod_no_container_statuses():
    pod = {"status": {"phase": "Pending"}}
    assert _summarize_status("Pod", pod) == "Pending (ready 0/0, restarts 0)"


def test_deployment_ready():
    dep = {"spec": {"replicas": 3}, "status": {"readyReplicas": 3}}
    assert _summarize_status("Deployment", dep) == "3/3 ready"


def test_deployment_rolling_out():
    dep = {"spec": {"replicas": 3}, "status": {"readyReplicas": 1}}
    assert _summarize_status("Deployment", dep) == "1/3 ready"


def test_statefulset_reuses_deployment_format():
    ss = {"spec": {"replicas": 2}, "status": {"readyReplicas": 2}}
    assert _summarize_status("StatefulSet", ss) == "2/2 ready"


def test_daemonset_ready():
    ds = {"status": {"numberReady": 3, "desiredNumberScheduled": 3}}
    assert _summarize_status("DaemonSet", ds) == "3/3 ready"


def test_service_clusterip():
    svc = {"spec": {"type": "ClusterIP", "clusterIP": "10.0.0.1"}, "status": {}}
    assert _summarize_status("Service", svc) == "ClusterIP 10.0.0.1"


def test_service_loadbalancer_with_external_ip():
    svc = {
        "spec": {"type": "LoadBalancer", "clusterIP": "10.0.0.1"},
        "status": {"loadBalancer": {"ingress": [{"ip": "1.2.3.4"}]}},
    }
    result = _summarize_status("Service", svc)
    assert "LoadBalancer" in result
    assert "1.2.3.4" in result


def test_pvc_bound_with_capacity():
    pvc = {"status": {"phase": "Bound", "capacity": {"storage": "10Gi"}}}
    assert _summarize_status("PersistentVolumeClaim", pvc) == "Bound (10Gi)"


def test_pvc_pending():
    pvc = {"status": {"phase": "Pending"}}
    assert _summarize_status("PersistentVolumeClaim", pvc) == "Pending"


def test_node_ready():
    node = {
        "status": {
            "conditions": [{"type": "Ready", "status": "True"}],
            "nodeInfo": {"kubeletVersion": "v1.29.0"},
        }
    }
    assert _summarize_status("Node", node) == "Ready (v1.29.0)"


def test_node_not_ready():
    node = {"status": {"conditions": [{"type": "Ready", "status": "False"}]}}
    assert _summarize_status("Node", node) == "NotReady"


def test_job_status():
    job = {"status": {"succeeded": 1, "failed": 0, "active": 0}}
    assert _summarize_status("Job", job) == "active=0 succeeded=1 failed=0"


def test_ingress_with_lb():
    ing = {"status": {"loadBalancer": {"ingress": [{"ip": "1.2.3.4"}, {"hostname": "example.com"}]}}}
    result = _summarize_status("Ingress", ing)
    assert result == "1.2.3.4,example.com"


def test_ingress_no_address():
    assert _summarize_status("Ingress", {"status": {}}) == "no address"


def test_unknown_kind_falls_back_to_phase():
    assert _summarize_status("CustomResource", {"status": {"phase": "Active"}}) == "Active"


def test_unknown_kind_no_phase_returns_empty():
    assert _summarize_status("CustomResource", {"status": {}}) == ""


def test_missing_status_key():
    assert _summarize_status("Pod", {}) == "Unknown (ready 0/0, restarts 0)"
