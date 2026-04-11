from __future__ import annotations
from grncli.customizations.commands import BasicCommand, display_output
from grncli.customizations.vks.validators import validate_id


class ListNodegroupsCommand(BasicCommand):
    NAME = 'list-nodegroups'
    DESCRIPTION = 'List node groups for a cluster'
    ARG_TABLE = [
        {'name': 'cluster-id', 'help_text': 'Cluster ID', 'required': True},
        {'name': 'page', 'help_text': 'Specific page number (0-based). Disables auto-pagination'},
        {'name': 'page-size', 'help_text': 'Number of items per page (default: 50)', 'default': '50'},
        {'name': 'no-paginate', 'help_text': 'Disable auto-pagination, return first page only',
         'action': 'store_true', 'default': False},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        validate_id(parsed_args.cluster_id, 'cluster-id')
        client = self._session.create_client('vks')
        path = f'/v1/clusters/{parsed_args.cluster_id}/node-groups'
        page_size = int(parsed_args.page_size)

        if parsed_args.page is not None:
            result = client.get(path, params={
                'page': int(parsed_args.page), 'pageSize': page_size,
            })
        elif parsed_args.no_paginate:
            result = client.get(path, params={
                'page': 0, 'pageSize': page_size,
            })
        else:
            result = client.get_all_pages(path, page_size=page_size)

        display_output(result, parsed_globals)
        return 0
