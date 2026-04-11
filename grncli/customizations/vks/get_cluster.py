from __future__ import annotations
from grncli.customizations.commands import BasicCommand, display_output
from grncli.customizations.vks.validators import validate_id

class GetClusterCommand(BasicCommand):
    NAME = 'get-cluster'
    DESCRIPTION = 'Get cluster details'
    ARG_TABLE = [
        {'name': 'cluster-id', 'help_text': 'Cluster ID', 'required': True},
    ]
    def _run_main(self, parsed_args, parsed_globals):
        validate_id(parsed_args.cluster_id, 'cluster-id')
        client = self._session.create_client('vks')
        result = client.get(f'/v1/clusters/{parsed_args.cluster_id}')
        display_output(result, parsed_globals)
        return 0
