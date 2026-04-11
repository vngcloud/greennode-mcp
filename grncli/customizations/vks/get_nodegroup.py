from __future__ import annotations
from grncli.customizations.commands import BasicCommand, display_output
from grncli.customizations.vks.validators import validate_id

class GetNodegroupCommand(BasicCommand):
    NAME = 'get-nodegroup'
    DESCRIPTION = 'Get node group details'
    ARG_TABLE = [
        {'name': 'cluster-id', 'help_text': 'Cluster ID', 'required': True},
        {'name': 'nodegroup-id', 'help_text': 'Node group ID', 'required': True},
    ]
    def _run_main(self, parsed_args, parsed_globals):
        validate_id(parsed_args.cluster_id, 'cluster-id')
        validate_id(parsed_args.nodegroup_id, 'nodegroup-id')
        client = self._session.create_client('vks')
        result = client.get(
            f'/v1/clusters/{parsed_args.cluster_id}/node-groups/{parsed_args.nodegroup_id}'
        )
        display_output(result, parsed_globals)
        return 0
