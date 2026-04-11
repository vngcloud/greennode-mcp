from __future__ import annotations

import sys

from grncli.customizations.commands import BasicCommand, display_output
from grncli.customizations.vks.validators import validate_id


class DeleteClusterCommand(BasicCommand):
    NAME = 'delete-cluster'
    DESCRIPTION = 'Delete a VKS cluster'
    ARG_TABLE = [
        {'name': 'cluster-id', 'help_text': 'Cluster ID', 'required': True},
        {'name': 'dry-run', 'help_text': 'Preview what will be deleted without executing',
         'action': 'store_true', 'default': False},
        {'name': 'force', 'help_text': 'Skip confirmation prompt',
         'action': 'store_true', 'default': False},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        validate_id(parsed_args.cluster_id, 'cluster-id')
        client = self._session.create_client('vks')
        cluster_id = parsed_args.cluster_id

        # Always fetch cluster info for preview
        cluster = client.get(f'/v1/clusters/{cluster_id}')
        nodegroups = client.get(
            f'/v1/clusters/{cluster_id}/node-groups',
            params={'page': 0, 'pageSize': 50},
        )

        # Show what will be deleted
        self._print_preview(cluster, nodegroups)

        if parsed_args.dry_run:
            sys.stdout.write("Run without --dry-run to delete.\n")
            return 0

        # Confirm unless --force
        if not parsed_args.force:
            response = input("\nAre you sure you want to delete this cluster? (yes/no): ")
            if response.strip().lower() != 'yes':
                sys.stdout.write("Delete cancelled.\n")
                return 0

        result = client.delete(f'/v1/clusters/{cluster_id}')
        display_output(result, parsed_globals)
        return 0

    def _print_preview(self, cluster: dict, nodegroups: dict) -> None:
        sys.stdout.write("The following resources will be deleted:\n\n")
        sys.stdout.write(f"Cluster:\n")
        sys.stdout.write(f"  ID:      {cluster.get('id', '')}\n")
        sys.stdout.write(f"  Name:    {cluster.get('name', '')}\n")
        sys.stdout.write(f"  Status:  {cluster.get('status', '')}\n")
        sys.stdout.write(f"  Version: {cluster.get('version', '')}\n")
        sys.stdout.write(f"  Nodes:   {cluster.get('numNodes', 0)}\n\n")

        items = nodegroups.get('items', [])
        if items:
            sys.stdout.write(f"Node groups ({len(items)}):\n")
            for ng in items:
                sys.stdout.write(f"  - {ng.get('name', '')} (ID: {ng.get('id', '')}, "
                                 f"nodes: {ng.get('numNodes', 0)})\n")
        else:
            sys.stdout.write("Node groups: none\n")

        sys.stdout.write("\nThis action is irreversible.\n")
