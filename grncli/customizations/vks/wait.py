from __future__ import annotations

import sys
import time

from grncli.customizations.commands import BasicCommand
from grncli.customizations.vks.validators import validate_id


DEFAULT_DELAY = 15  # seconds between polls
DEFAULT_MAX_ATTEMPTS = 40  # 40 * 15s = 10 minutes


class WaitClusterActiveCommand(BasicCommand):
    NAME = 'wait-cluster-active'
    DESCRIPTION = 'Wait until cluster reaches ACTIVE status'
    ARG_TABLE = [
        {'name': 'cluster-id', 'help_text': 'Cluster ID', 'required': True},
        {'name': 'delay', 'help_text': 'Seconds between polls (default: 15)', 'default': '15'},
        {'name': 'max-attempts', 'help_text': 'Maximum poll attempts (default: 40)', 'default': '40'},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        validate_id(parsed_args.cluster_id, 'cluster-id')
        return _wait_for_status(
            self._session, parsed_args.cluster_id,
            target_status='ACTIVE',
            resource_type='cluster',
            delay=int(parsed_args.delay),
            max_attempts=int(parsed_args.max_attempts),
        )


def _wait_for_status(
    session, cluster_id: str, target_status: str,
    resource_type: str, delay: int, max_attempts: int,
) -> int:
    client = session.create_client('vks')
    for attempt in range(1, max_attempts + 1):
        try:
            result = client.get(f'/v1/clusters/{cluster_id}')
            status = result.get('status', '')
            sys.stderr.write(
                f"\rWaiting for {resource_type} {cluster_id}: "
                f"{status} (attempt {attempt}/{max_attempts})"
            )
            sys.stderr.flush()

            if status == target_status:
                sys.stderr.write('\n')
                sys.stdout.write(
                    f"Successfully waited for {resource_type} "
                    f"to reach {target_status}\n"
                )
                return 0

            if status in ('ERROR', 'FAILED'):
                sys.stderr.write('\n')
                sys.stderr.write(
                    f"Waiter failed: {resource_type} reached {status}\n"
                )
                return 255

        except RuntimeError:
            sys.stderr.write(
                f"\rWaiting for {resource_type} {cluster_id}: "
                f"error fetching status (attempt {attempt}/{max_attempts})"
            )
            sys.stderr.flush()

        if attempt < max_attempts:
            time.sleep(delay)

    sys.stderr.write('\n')
    sys.stderr.write(
        f"Waiter timed out after {max_attempts} attempts\n"
    )
    return 255
