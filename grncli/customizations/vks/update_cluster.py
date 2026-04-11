from __future__ import annotations
from grncli.customizations.commands import BasicCommand, display_output
from grncli.customizations.vks.validators import validate_id


class UpdateClusterCommand(BasicCommand):
    NAME = 'update-cluster'
    DESCRIPTION = 'Update a VKS cluster'
    ARG_TABLE = [
        {'name': 'cluster-id', 'help_text': 'Cluster ID', 'required': True},
        # Required fields per API spec
        {'name': 'k8s-version', 'help_text': 'Kubernetes version', 'required': True},
        {'name': 'whitelist-node-cidrs', 'help_text': 'Whitelist CIDRs (comma-separated, min 1)', 'required': True},
        # Optional fields
        {'name': 'enabled-load-balancer-plugin', 'help_text': 'Enable load balancer plugin', 'action': 'store_true', 'default': False},
        {'name': 'no-load-balancer-plugin', 'help_text': 'Disable load balancer plugin', 'action': 'store_true', 'default': False},
        {'name': 'enabled-block-store-csi-plugin', 'help_text': 'Enable block store CSI plugin', 'action': 'store_true', 'default': False},
        {'name': 'no-block-store-csi-plugin', 'help_text': 'Disable block store CSI plugin', 'action': 'store_true', 'default': False},
        {'name': 'dry-run', 'help_text': 'Validate parameters without updating', 'action': 'store_true', 'default': False},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        validate_id(parsed_args.cluster_id, 'cluster-id')
        client = self._session.create_client('vks')
        body = {
            'version': parsed_args.k8s_version,
            'whitelistNodeCIDRs': [
                c.strip() for c in parsed_args.whitelist_node_cidrs.split(',')
            ],
        }

        if parsed_args.enabled_load_balancer_plugin:
            body['enabledLoadBalancerPlugin'] = True
        elif parsed_args.no_load_balancer_plugin:
            body['enabledLoadBalancerPlugin'] = False

        if parsed_args.enabled_block_store_csi_plugin:
            body['enabledBlockStoreCsiPlugin'] = True
        elif parsed_args.no_block_store_csi_plugin:
            body['enabledBlockStoreCsiPlugin'] = False

        if parsed_args.dry_run:
            import sys
            sys.stdout.write("=== DRY RUN: Update cluster ===\n\n")
            sys.stdout.write(f"Cluster ID: {parsed_args.cluster_id}\n")
            sys.stdout.write(f"New version: {body['version']}\n")
            sys.stdout.write(f"Whitelist CIDRs: {', '.join(body['whitelistNodeCIDRs'])}\n")
            if 'enabledLoadBalancerPlugin' in body:
                sys.stdout.write(f"Load balancer plugin: {body['enabledLoadBalancerPlugin']}\n")
            if 'enabledBlockStoreCsiPlugin' in body:
                sys.stdout.write(f"Block store CSI plugin: {body['enabledBlockStoreCsiPlugin']}\n")
            sys.stdout.write("\nRun without --dry-run to update.\n")
            return 0

        result = client.put(f'/v1/clusters/{parsed_args.cluster_id}', json=body)
        display_output(result, parsed_globals)
        return 0
