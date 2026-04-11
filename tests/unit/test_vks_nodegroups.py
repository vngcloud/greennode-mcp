# greenode-cli/tests/unit/test_vks_nodegroups.py
from __future__ import annotations
import io, sys
from argparse import Namespace
from unittest.mock import MagicMock
import pytest
from grncli.customizations.vks.list_nodegroups import ListNodegroupsCommand
from grncli.customizations.vks.get_nodegroup import GetNodegroupCommand
from grncli.customizations.vks.create_nodegroup import CreateNodegroupCommand
from grncli.customizations.vks.update_nodegroup import UpdateNodegroupCommand
from grncli.customizations.vks.delete_nodegroup import DeleteNodegroupCommand

@pytest.fixture
def session():
    s = MagicMock()
    client = MagicMock()
    s.create_client.return_value = client
    return s, client

class TestListNodegroups:
    def test_calls_api(self, session):
        s, client = session
        client.get.return_value = {"items": [], "total": 0}
        cmd = ListNodegroupsCommand(s)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(cluster_id='c-123', page='0', page_size=50, no_paginate=False),
                Namespace(output='json', query=None, color='off'))
        finally:
            sys.stdout = old_stdout
        assert rc == 0
        client.get.assert_called_once_with('/v1/clusters/c-123/node-groups',
            params={'page': 0, 'pageSize': 50})

class TestGetNodegroup:
    def test_calls_api(self, session):
        s, client = session
        client.get.return_value = {"id": "ng-1", "name": "default"}
        cmd = GetNodegroupCommand(s)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(cluster_id='c-123', nodegroup_id='ng-1'),
                Namespace(output='json', query=None, color='off'))
        finally:
            sys.stdout = old_stdout
        assert rc == 0
        client.get.assert_called_once_with('/v1/clusters/c-123/node-groups/ng-1')

class TestCreateNodegroup:
    def test_calls_api(self, session):
        s, client = session
        client.post.return_value = {"id": "ng-new"}
        cmd = CreateNodegroupCommand(s)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(cluster_id='c-123', name='workers', num_nodes=3,
                image_id='img-1', flavor_id='flav-1', disk_size=100, disk_type='SSD',
                enable_private_nodes=False, security_groups=None, ssh_key_id='ssh-123',
                subnet_id=None, labels=None, taints=None, enable_encryption_volume=False,
                dry_run=False),
                Namespace(output='json', query=None, color='off'))
        finally:
            sys.stdout = old_stdout
        assert rc == 0
        client.post.assert_called_once()
        body = client.post.call_args[1]['json']
        assert body['name'] == 'workers'
        assert body['numNodes'] == 3

class TestUpdateNodegroup:
    def test_calls_api(self, session):
        s, client = session
        client.put.return_value = {"id": "ng-1"}
        cmd = UpdateNodegroupCommand(s)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(cluster_id='c-123', nodegroup_id='ng-1',
                image_id='img-2', num_nodes=5, security_groups=None,
                labels=None, taints=None,
                auto_scale_min=None, auto_scale_max=None,
                upgrade_strategy=None, upgrade_max_surge=None, upgrade_max_unavailable=None,
                dry_run=False),
                Namespace(output='json', query=None, color='off'))
        finally:
            sys.stdout = old_stdout
        assert rc == 0
        client.put.assert_called_once()

class TestDeleteNodegroup:
    def test_calls_api(self, session):
        s, client = session
        client.get.return_value = {"id": "ng-1", "name": "default", "status": "ACTIVE", "numNodes": 3}
        client.delete.return_value = {"message": "Deleted"}
        cmd = DeleteNodegroupCommand(s)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(cluster_id='c-123', nodegroup_id='ng-1',
                force_delete=False, dry_run=False, force=True),
                Namespace(output='json', query=None, color='off'))
        finally:
            sys.stdout = old_stdout
        assert rc == 0
        client.delete.assert_called_once()
