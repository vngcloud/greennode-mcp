# greenode-cli/tests/unit/test_vks_clusters.py
from __future__ import annotations
import io, sys
from argparse import Namespace
from unittest.mock import MagicMock
import pytest
from grncli.customizations.vks.list_clusters import ListClustersCommand
from grncli.customizations.vks.get_cluster import GetClusterCommand
from grncli.customizations.vks.create_cluster import CreateClusterCommand
from grncli.customizations.vks.update_cluster import UpdateClusterCommand
from grncli.customizations.vks.delete_cluster import DeleteClusterCommand

@pytest.fixture
def session():
    s = MagicMock()
    client = MagicMock()
    s.create_client.return_value = client
    return s, client

class TestListClusters:
    def test_calls_api(self, session):
        s, client = session
        client.get.return_value = {"items": [], "total": 0}
        cmd = ListClustersCommand(s)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(page='0', page_size=50, no_paginate=False),
                Namespace(output='json', query=None, color='off'))
        finally:
            sys.stdout = old_stdout
        assert rc == 0
        client.get.assert_called_once_with('/v1/clusters', params={'page': 0, 'pageSize': 50})

class TestGetCluster:
    def test_calls_api(self, session):
        s, client = session
        client.get.return_value = {"id": "abc", "name": "test", "status": "ACTIVE"}
        cmd = GetClusterCommand(s)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(cluster_id='abc'), Namespace(output='json', query=None, color='off'))
        finally:
            sys.stdout = old_stdout
        assert rc == 0
        client.get.assert_called_once_with('/v1/clusters/abc')

class TestCreateCluster:
    def test_calls_api(self, session):
        s, client = session
        client.post.return_value = {"id": "new-id", "name": "new-cluster"}
        cmd = CreateClusterCommand(s)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(
                Namespace(name='new-cluster', k8s_version='v1.30.1', network_type='CALICO',
                    vpc_id='vpc-123', subnet_id='sub-456', cidr='172.16.0.0/16',
                    description=None,
                    node_group_name='default', flavor_id='flav-1', image_id='img-1',
                    disk_size=100, disk_type='SSD', num_nodes=3,
                    enable_private_cluster=False, release_channel='STABLE',
                    enable_private_nodes=False, ssh_key_id='ssh-123',
                    security_groups=None, labels=None, taints=None,
                    no_load_balancer_plugin=False, no_block_store_csi_plugin=False,
                    enabled_load_balancer_plugin=False, enabled_block_store_csi_plugin=False,
                    dry_run=False),
                Namespace(output='json', query=None, color='off'))
        finally:
            sys.stdout = old_stdout
        assert rc == 0
        client.post.assert_called_once()
        body = client.post.call_args[1]['json']
        assert body['name'] == 'new-cluster'

class TestUpdateCluster:
    def test_calls_api(self, session):
        s, client = session
        client.put.return_value = {"id": "abc", "name": "test"}
        cmd = UpdateClusterCommand(s)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(cluster_id='abc', k8s_version='v1.31.0',
                    whitelist_node_cidrs='0.0.0.0/0',
                    enabled_load_balancer_plugin=False, no_load_balancer_plugin=False,
                    enabled_block_store_csi_plugin=False, no_block_store_csi_plugin=False,
                    dry_run=False),
                Namespace(output='json', query=None, color='off'))
        finally:
            sys.stdout = old_stdout
        assert rc == 0
        client.put.assert_called_once()

class TestDeleteCluster:
    def test_calls_api(self, session):
        s, client = session
        client.get.side_effect = [
            {"id": "abc", "name": "test", "status": "ACTIVE", "version": "v1.30", "numNodes": 3},
            {"items": [], "total": 0},
        ]
        client.delete.return_value = {"id": "abc", "status": "DELETING"}
        cmd = DeleteClusterCommand(s)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(cluster_id='abc', dry_run=False, force=True), Namespace(output='json', query=None, color='off'))
        finally:
            sys.stdout = old_stdout
        assert rc == 0
        client.delete.assert_called_once_with('/v1/clusters/abc')

