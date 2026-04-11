from __future__ import annotations

import re
import sys

from grncli.customizations.commands import BasicCommand, display_output


class CreateClusterCommand(BasicCommand):
    NAME = 'create-cluster'
    DESCRIPTION = 'Create a new VKS cluster'
    ARG_TABLE = [
        # Cluster settings (required)
        {'name': 'name', 'help_text': 'Cluster name', 'required': True},
        {'name': 'k8s-version', 'help_text': 'Kubernetes version', 'required': True},
        {'name': 'network-type', 'help_text': 'Network type (CALICO, CILIUM_OVERLAY, CILIUM_NATIVE_ROUTING)', 'required': True},
        {'name': 'vpc-id', 'help_text': 'VPC ID', 'required': True},
        {'name': 'subnet-id', 'help_text': 'Subnet ID', 'required': True},
        # Cluster settings (optional)
        {'name': 'cidr', 'help_text': 'CIDR block (required for CALICO and CILIUM_OVERLAY)'},
        {'name': 'description', 'help_text': 'Cluster description'},
        {'name': 'enable-private-cluster', 'help_text': 'Enable private cluster', 'action': 'store_true', 'default': False},
        {'name': 'release-channel', 'help_text': 'Release channel (RAPID, STABLE)', 'default': 'STABLE'},
        {'name': 'enabled-load-balancer-plugin', 'help_text': 'Enable load balancer plugin', 'action': 'store_true', 'default': False},
        {'name': 'no-load-balancer-plugin', 'help_text': 'Disable load balancer plugin', 'action': 'store_true', 'default': False},
        {'name': 'enabled-block-store-csi-plugin', 'help_text': 'Enable block store CSI plugin', 'action': 'store_true', 'default': False},
        {'name': 'no-block-store-csi-plugin', 'help_text': 'Disable block store CSI plugin', 'action': 'store_true', 'default': False},
        # Node group settings (required)
        {'name': 'node-group-name', 'help_text': 'Default node group name', 'required': True},
        {'name': 'flavor-id', 'help_text': 'Flavor ID for node group', 'required': True},
        {'name': 'image-id', 'help_text': 'Image ID for node group', 'required': True},
        {'name': 'disk-type', 'help_text': 'Disk type ID', 'required': True},
        {'name': 'ssh-key-id', 'help_text': 'SSH key ID for node group', 'required': True},
        # Node group settings (optional with defaults)
        {'name': 'disk-size', 'help_text': 'Disk size in GiB (20-5000, default: 100)', 'default': '100'},
        {'name': 'num-nodes', 'help_text': 'Number of nodes (default: 1)', 'default': '1'},
        {'name': 'enable-private-nodes', 'help_text': 'Enable private nodes', 'action': 'store_true', 'default': False},
        {'name': 'security-groups', 'help_text': 'Security group IDs (comma-separated)'},
        {'name': 'labels', 'help_text': 'Node labels as key=value pairs (comma-separated, e.g. env=prod,tier=app)'},
        {'name': 'taints', 'help_text': 'Node taints as key=value:effect (comma-separated, e.g. dedicated=gpu:NoSchedule)'},
        {'name': 'dry-run', 'help_text': 'Validate parameters without creating the cluster',
         'action': 'store_true', 'default': False},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        client = self._session.create_client('vks')

        # Build node group
        node_group = {
            'name': parsed_args.node_group_name,
            'flavorId': parsed_args.flavor_id,
            'imageId': parsed_args.image_id,
            'diskSize': int(parsed_args.disk_size),
            'diskType': parsed_args.disk_type,
            'numNodes': int(parsed_args.num_nodes),
            'enablePrivateNodes': parsed_args.enable_private_nodes,
            'sshKeyId': parsed_args.ssh_key_id,
            'upgradeConfig': {
                'maxSurge': 1,
                'maxUnavailable': 0,
                'strategy': 'SURGE',
            },
            'subnetId': parsed_args.subnet_id,
            'securityGroups': [],
        }
        if parsed_args.security_groups:
            node_group['securityGroups'] = [
                s.strip() for s in parsed_args.security_groups.split(',')
            ]
        if parsed_args.labels:
            node_group['labels'] = _parse_labels(parsed_args.labels)
        if parsed_args.taints:
            node_group['taints'] = _parse_taints(parsed_args.taints)

        # Build cluster body
        # Default: both plugins enabled (match API defaults)
        load_balancer = not parsed_args.no_load_balancer_plugin
        block_store = not parsed_args.no_block_store_csi_plugin

        body = {
            'name': parsed_args.name,
            'version': parsed_args.k8s_version,
            'networkType': parsed_args.network_type,
            'vpcId': parsed_args.vpc_id,
            'subnetId': parsed_args.subnet_id,
            'enablePrivateCluster': parsed_args.enable_private_cluster,
            'releaseChannel': parsed_args.release_channel,
            'enabledBlockStoreCsiPlugin': block_store,
            'enabledLoadBalancerPlugin': load_balancer,
            'enabledServiceEndpoint': False,
            'azStrategy': 'SINGLE',
            'nodeGroups': [node_group],
        }
        if parsed_args.cidr:
            body['cidr'] = parsed_args.cidr
        if parsed_args.description:
            body['description'] = parsed_args.description

        if parsed_args.dry_run:
            return self._validate(parsed_args, node_group)

        result = client.post('/v1/clusters', json=body)
        display_output(result, parsed_globals)
        return 0

    def _validate(self, parsed_args, node_group: dict) -> int:
        errors = []
        CLUSTER_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9\-]{3,18}[a-z0-9]$')
        NG_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9-]{3,13}[a-z0-9]$')

        # Cluster name
        if not CLUSTER_NAME_RE.match(parsed_args.name):
            errors.append(
                f"Cluster name '{parsed_args.name}' is invalid. "
                "Must be 5-20 chars, lowercase alphanumeric and hyphens, "
                "start/end with alphanumeric."
            )

        # CIDR required for CALICO and CILIUM_OVERLAY
        if parsed_args.network_type in ('CALICO', 'CILIUM_OVERLAY') and not parsed_args.cidr:
            errors.append(
                f"--cidr is required when network-type is {parsed_args.network_type}"
            )

        # Node group name
        ng_name = node_group.get('name', '')
        if not NG_NAME_RE.match(ng_name):
            errors.append(
                f"Node group name '{ng_name}' is invalid. "
                "Must be 5-15 chars, lowercase alphanumeric and hyphens, "
                "start/end with alphanumeric."
            )

        # Disk size
        disk_size = node_group.get('diskSize', 0)
        if not (20 <= disk_size <= 5000):
            errors.append(f"Disk size {disk_size} out of range (20-5000 GiB)")

        # Num nodes
        num_nodes = node_group.get('numNodes', 0)
        if not (0 <= num_nodes <= 10):
            errors.append(f"Number of nodes {num_nodes} out of range (0-10)")

        sys.stdout.write("=== DRY RUN: Validation results ===\n\n")
        if errors:
            sys.stdout.write(f"Found {len(errors)} error(s):\n")
            for err in errors:
                sys.stdout.write(f"  - {err}\n")
            return 1
        else:
            sys.stdout.write("All parameters are valid. "
                             "Run without --dry-run to create the cluster.\n")
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
