from __future__ import annotations
from grncli.customizations.commands import BasicCommand, display_output
from grncli.customizations.vks.validators import validate_id


class UpdateNodegroupCommand(BasicCommand):
    NAME = 'update-nodegroup'
    DESCRIPTION = 'Update a node group'
    ARG_TABLE = [
        # Required
        {'name': 'cluster-id', 'help_text': 'Cluster ID', 'required': True},
        {'name': 'nodegroup-id', 'help_text': 'Node group ID', 'required': True},
        {'name': 'image-id', 'help_text': 'Image ID (always required)', 'required': True},
        # Optional
        {'name': 'num-nodes', 'help_text': 'New number of nodes'},
        {'name': 'security-groups', 'help_text': 'Security group IDs (comma-separated)'},
        {'name': 'labels', 'help_text': 'Node labels as key=value pairs (comma-separated)'},
        {'name': 'taints', 'help_text': 'Node taints as key=value:effect (comma-separated)'},
        {'name': 'auto-scale-min', 'help_text': 'Auto-scale minimum nodes'},
        {'name': 'auto-scale-max', 'help_text': 'Auto-scale maximum nodes'},
        {'name': 'upgrade-strategy', 'help_text': 'Upgrade strategy (SURGE)'},
        {'name': 'upgrade-max-surge', 'help_text': 'Max surge during upgrade'},
        {'name': 'upgrade-max-unavailable', 'help_text': 'Max unavailable during upgrade'},
        {'name': 'dry-run', 'help_text': 'Preview update without executing', 'action': 'store_true', 'default': False},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        validate_id(parsed_args.cluster_id, 'cluster-id')
        validate_id(parsed_args.nodegroup_id, 'nodegroup-id')
        client = self._session.create_client('vks')
        body = {'imageId': parsed_args.image_id}

        if parsed_args.num_nodes:
            body['numNodes'] = int(parsed_args.num_nodes)
        if parsed_args.security_groups:
            body['securityGroups'] = [
                s.strip() for s in parsed_args.security_groups.split(',')
            ]
        if parsed_args.labels:
            body['labels'] = _parse_labels(parsed_args.labels)
        if parsed_args.taints:
            body['taints'] = _parse_taints(parsed_args.taints)

        # Auto-scale config
        if parsed_args.auto_scale_min or parsed_args.auto_scale_max:
            body['autoScaleConfig'] = {}
            if parsed_args.auto_scale_min:
                body['autoScaleConfig']['minSize'] = int(parsed_args.auto_scale_min)
            if parsed_args.auto_scale_max:
                body['autoScaleConfig']['maxSize'] = int(parsed_args.auto_scale_max)

        # Upgrade config
        if (parsed_args.upgrade_strategy or parsed_args.upgrade_max_surge
                or parsed_args.upgrade_max_unavailable):
            body['upgradeConfig'] = {}
            if parsed_args.upgrade_strategy:
                body['upgradeConfig']['strategy'] = parsed_args.upgrade_strategy
            if parsed_args.upgrade_max_surge:
                body['upgradeConfig']['maxSurge'] = int(parsed_args.upgrade_max_surge)
            if parsed_args.upgrade_max_unavailable:
                body['upgradeConfig']['maxUnavailable'] = int(parsed_args.upgrade_max_unavailable)

        if parsed_args.dry_run:
            import sys
            sys.stdout.write("=== DRY RUN: Update node group ===\n\n")
            sys.stdout.write(f"Cluster ID: {parsed_args.cluster_id}\n")
            sys.stdout.write(f"Node group ID: {parsed_args.nodegroup_id}\n")
            for key, value in body.items():
                sys.stdout.write(f"  {key}: {value}\n")
            sys.stdout.write("\nRun without --dry-run to update.\n")
            return 0

        result = client.put(
            f'/v1/clusters/{parsed_args.cluster_id}'
            f'/node-groups/{parsed_args.nodegroup_id}',
            json=body,
        )
        display_output(result, parsed_globals)
        return 0


def _parse_labels(labels_str: str) -> dict:
    """Parse 'key1=val1,key2=val2' into {'key1': 'val1', 'key2': 'val2'}."""
    result = {}
    for pair in labels_str.split(','):
        pair = pair.strip()
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key.strip()] = value.strip()
    return result


def _parse_taints(taints_str: str) -> list[dict]:
    """Parse 'key=value:effect,...' into [{'key': k, 'value': v, 'effect': e}]."""
    result = []
    for taint in taints_str.split(','):
        taint = taint.strip()
        if ':' in taint:
            kv, effect = taint.rsplit(':', 1)
            if '=' in kv:
                key, value = kv.split('=', 1)
            else:
                key, value = kv, ''
            result.append({
                'key': key.strip(),
                'value': value.strip(),
                'effect': effect.strip(),
            })
    return result
