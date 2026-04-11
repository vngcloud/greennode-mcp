from __future__ import annotations

import sys

from grncli.customizations.commands import BasicCommand, display_output
from grncli.customizations.vks.validators import validate_id


class DeleteNodegroupCommand(BasicCommand):
    NAME = 'delete-nodegroup'
    DESCRIPTION = 'Delete a node group'
    ARG_TABLE = [
        {'name': 'cluster-id', 'help_text': 'Cluster ID', 'required': True},
        {'name': 'nodegroup-id', 'help_text': 'Node group ID', 'required': True},
        {'name': 'force-delete', 'help_text': 'Force delete on API side', 'action': 'store_true', 'default': False},
        {'name': 'dry-run', 'help_text': 'Preview what will be deleted without executing',
         'action': 'store_true', 'default': False},
        {'name': 'force', 'help_text': 'Skip confirmation prompt',
         'action': 'store_true', 'default': False},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        validate_id(parsed_args.cluster_id, 'cluster-id')
        validate_id(parsed_args.nodegroup_id, 'nodegroup-id')
        client = self._session.create_client('vks')
        cluster_id = parsed_args.cluster_id
        nodegroup_id = parsed_args.nodegroup_id

        # Fetch nodegroup info for preview
        ng = client.get(
            f'/v1/clusters/{cluster_id}/node-groups/{nodegroup_id}'
        )

        # Show what will be deleted
        sys.stdout.write("The following node group will be deleted:\n\n")
        sys.stdout.write(f"  ID:      {ng.get('id', '')}\n")
        sys.stdout.write(f"  Name:    {ng.get('name', '')}\n")
        sys.stdout.write(f"  Status:  {ng.get('status', '')}\n")
        sys.stdout.write(f"  Nodes:   {ng.get('numNodes', 0)}\n\n")
        sys.stdout.write("This action is irreversible.\n")

        if parsed_args.dry_run:
            sys.stdout.write("Run without --dry-run to delete.\n")
            return 0

        # Confirm unless --force
        if not parsed_args.force:
            response = input("\nAre you sure you want to delete this node group? (yes/no): ")
            if response.strip().lower() != 'yes':
                sys.stdout.write("Delete cancelled.\n")
                return 0

        params = {}
        if parsed_args.force_delete:
            params['forceDelete'] = True
        result = client.delete(
            f'/v1/clusters/{cluster_id}/node-groups/{nodegroup_id}',
            params=params if params else None,
        )
        display_output(result, parsed_globals)
        return 0
