# greenode-cli/grncli/customizations/configure/get.py
from __future__ import annotations

import sys

from grncli.customizations.commands import BasicCommand


class ConfigureGetCommand(BasicCommand):
    NAME = 'get'
    DESCRIPTION = 'Get a config value'
    ARG_TABLE = [
        {'name': 'varname', 'positional_arg': True,
         'help_text': 'Config variable name (e.g. region, profile.staging.region)'},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        varname = parsed_args.varname
        if '.' not in varname:
            value = self._get_simple(varname)
        else:
            value = self._get_dotted(varname)
        if value is None:
            return 1

        # Mask sensitive values
        if varname.endswith(('client_id', 'client_secret')):
            value = '*' * 16 + str(value)[-4:]

        sys.stdout.write(str(value) + '\n')
        return 0

    def _get_simple(self, varname):
        try:
            config = self._session.get_scoped_config()
            if varname in config:
                return config[varname]
        except Exception:
            pass
        try:
            creds = self._session.get_credentials()
            if varname in creds:
                return creds[varname]
        except Exception:
            pass
        return None

    def _get_dotted(self, varname):
        parts = varname.split('.')
        if len(parts) == 2 and parts[0] == 'default':
            return self._get_from_profile('default', parts[1])
        if len(parts) == 3 and parts[0] == 'profile':
            return self._get_from_profile(parts[1], parts[2])
        return None

    def _get_from_profile(self, profile, key):
        original_profile = self._session.profile
        try:
            self._session.profile = profile
            return self._get_simple(key)
        finally:
            self._session.profile = original_profile
