from __future__ import annotations
from grncli.customizations.commands import BasicCommand, display_output
from grncli.customizations.vks.validators import validate_id


class CreateNodegroupCommand(BasicCommand):
    NAME = 'create-nodegroup'
    DESCRIPTION = 'Create a new node group'
    ARG_TABLE = [
        # Required fields
        {'name': 'cluster-id', 'help_text': 'Cluster ID', 'required': True},
        {'name': 'name', 'help_text': 'Node group name', 'required': True},
        {'name': 'image-id', 'help_text': 'Image ID', 'required': True},
        {'name': 'flavor-id', 'help_text': 'Flavor ID', 'required': True},
        {'name': 'disk-type', 'help_text': 'Disk type ID', 'required': True},
        {'name': 'ssh-key-id', 'help_text': 'SSH key ID', 'required': True},
        {'name': 'enable-private-nodes', 'help_text': 'Enable private nodes', 'action': 'store_true', 'default': False},
        # Optional with defaults
        {'name': 'num-nodes', 'help_text': 'Number of nodes (default: 1)', 'default': '1'},
        {'name': 'disk-size', 'help_text': 'Disk size in GiB (20-5000, default: 100)', 'default': '100'},
        {'name': 'security-groups', 'help_text': 'Security group IDs (comma-separated)'},
        {'name': 'subnet-id', 'help_text': 'Subnet ID for node group'},
        {'name': 'labels', 'help_text': 'Node labels as key=value pairs (comma-separated, e.g. env=prod,tier=app)'},
        {'name': 'taints', 'help_text': 'Node taints as key=value:effect (comma-separated, e.g. dedicated=gpu:NoSchedule)'},
        {'name': 'enable-encryption-volume', 'help_text': 'Enable volume encryption', 'action': 'store_true', 'default': False},
        {'name': 'dry-run', 'help_text': 'Validate parameters without creating', 'action': 'store_true', 'default': False},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        validate_id(parsed_args.cluster_id, 'cluster-id')
        client = self._session.create_client('vks')
        body = {
            'name': parsed_args.name,
            'numNodes': int(parsed_args.num_nodes),
            'imageId': parsed_args.image_id,
            'flavorId': parsed_args.flavor_id,
            'diskSize': int(parsed_args.disk_size),
            'diskType': parsed_args.disk_type,
            'enablePrivateNodes': parsed_args.enable_private_nodes,
            'sshKeyId': parsed_args.ssh_key_id,
            'enabledEncryptionVolume': parsed_args.enable_encryption_volume,
            'securityGroups': [],
            'upgradeConfig': {
                'maxSurge': 1,
                'maxUnavailable': 0,
                'strategy': 'SURGE',
            },
        }
        if parsed_args.security_groups:
            body['securityGroups'] = [
                s.strip() for s in parsed_args.security_groups.split(',')
            ]
        if parsed_args.subnet_id:
            body['subnetId'] = parsed_args.subnet_id
        if parsed_args.labels:
            body['labels'] = _parse_labels(parsed_args.labels)
        if parsed_args.taints:
            body['taints'] = _parse_taints(parsed_args.taints)

        if parsed_args.dry_run:
            return self._validate(parsed_args, body)

        result = client.post(
            f'/v1/clusters/{parsed_args.cluster_id}/node-groups', json=body
        )
        display_output(result, parsed_globals)
        return 0


    def _validate(self, parsed_args, body):
        import re
        import sys
        errors = []
        NG_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9-]{3,13}[a-z0-9]$')

        if not NG_NAME_RE.match(parsed_args.name):
            errors.append(f"Node group name '{parsed_args.name}' is invalid. Must be 5-15 chars, lowercase alphanumeric and hyphens.")

        disk_size = body.get('diskSize', 0)
        if not (20 <= disk_size <= 5000):
            errors.append(f"Disk size {disk_size} out of range (20-5000 GiB)")

        num_nodes = body.get('numNodes', 0)
        if not (0 <= num_nodes <= 10):
            errors.append(f"Number of nodes {num_nodes} out of range (0-10)")

        sys.stdout.write("=== DRY RUN: Validation results ===\n\n")
        if errors:
            sys.stdout.write(f"Found {len(errors)} error(s):\n")
            for err in errors:
                sys.stdout.write(f"  - {err}\n")
            return 1
        else:
            sys.stdout.write("All parameters are valid. Run without --dry-run to create.\n")
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
