from __future__ import annotations
from grncli.customizations.commands import BasicCommand, display_output


class ListClustersCommand(BasicCommand):
    NAME = 'list-clusters'
    DESCRIPTION = 'List all VKS clusters'
    ARG_TABLE = [
        {'name': 'page', 'help_text': 'Specific page number (0-based). Disables auto-pagination'},
        {'name': 'page-size', 'help_text': 'Number of items per page (default: 50)', 'default': '50'},
        {'name': 'no-paginate', 'help_text': 'Disable auto-pagination, return first page only',
         'action': 'store_true', 'default': False},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        client = self._session.create_client('vks')
        page_size = int(parsed_args.page_size)

        if parsed_args.page is not None:
            # Specific page requested
            result = client.get('/v1/clusters', params={
                'page': int(parsed_args.page), 'pageSize': page_size,
            })
        elif parsed_args.no_paginate:
            # First page only
            result = client.get('/v1/clusters', params={
                'page': 0, 'pageSize': page_size,
            })
        else:
            # Auto-paginate: fetch all pages
            result = client.get_all_pages('/v1/clusters', page_size=page_size)

        display_output(result, parsed_globals)
        return 0
