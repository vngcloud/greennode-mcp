# greenode-cli/grncli/customizations/configure/list.py
from __future__ import annotations

import os
import sys

from grncli.customizations.commands import BasicCommand


class ConfigureListCommand(BasicCommand):
    NAME = 'list'
    DESCRIPTION = 'Show config values and their sources'

    def _run_main(self, parsed_args, parsed_globals):
        profile = self._session.profile
        entries = []
        entries.append(self._resolve_profile(profile))
        entries.append(self._resolve_credential('client_id'))
        entries.append(self._resolve_credential('client_secret'))
        entries.append(self._resolve_config('region', 'GRN_DEFAULT_REGION'))
        entries.append(self._resolve_config('output', 'GRN_DEFAULT_OUTPUT'))

        header = f"{'Name':>14s}{'Value':>24s}{'Type':>16s}    {'Location'}"
        sep = f"{'----':>14s}{'-----':>24s}{'----':>16s}    {'--------'}"
        sys.stdout.write(header + '\n')
        sys.stdout.write(sep + '\n')
        for name, value, source_type, location in entries:
            sys.stdout.write(
                f'{name:>14s}{value:>24s}{str(source_type):>16s}'
                f'    {str(location)}\n'
            )
        return 0

    def _mask_value(self, value):
        if len(value) <= 4:
            return value
        return '*' * 16 + value[-4:]

    def _resolve_profile(self, profile):
        env_profile = os.environ.get('GRN_PROFILE')
        if env_profile:
            return ('profile', env_profile, 'env', 'GRN_PROFILE')
        if profile and profile != 'default':
            return ('profile', profile, 'manual', '--profile')
        return ('profile', '<not set>', 'None', 'None')

    def _resolve_credential(self, key):
        env_map = {'client_id': 'GRN_CLIENT_ID', 'client_secret': 'GRN_CLIENT_SECRET'}
        env_var = env_map.get(key, '')
        env_val = os.environ.get(env_var)
        if env_val:
            return (key, self._mask_value(env_val), 'env', env_var)
        try:
            creds = self._session.get_credentials()
            value = creds.get(key)
            if value:
                return (key, self._mask_value(value), 'config-file', self._session.credentials_file)
        except Exception:
            pass
        return (key, '<not set>', 'None', 'None')

    def _resolve_config(self, key, env_var):
        env_val = os.environ.get(env_var)
        if env_val:
            return (key, env_val, 'env', env_var)
        try:
            config = self._session.get_scoped_config()
            value = config.get(key)
            if value:
                return (key, value, 'config-file', self._session.config_file)
        except Exception:
            pass
        return (key, '<not set>', 'None', 'None')
