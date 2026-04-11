# greenode-cli/grncli/customizations/configure/set.py
from __future__ import annotations

from grncli.customizations.commands import BasicCommand
from grncli.customizations.configure.writer import ConfigFileWriter

CREDS_KEYS = {'client_id', 'client_secret'}


class ConfigureSetCommand(BasicCommand):
    NAME = 'set'
    DESCRIPTION = 'Set a config value'
    ARG_TABLE = [
        {'name': 'varname', 'positional_arg': True, 'help_text': 'Config variable name'},
        {'name': 'value', 'positional_arg': True, 'help_text': 'New value'},
    ]

    def __init__(self, session, config_writer=None):
        super().__init__(session)
        self._config_writer = config_writer or ConfigFileWriter()

    def _run_main(self, parsed_args, parsed_globals):
        varname = parsed_args.varname
        value = parsed_args.value
        profile, key = self._parse_varname(varname)

        if key in CREDS_KEYS:
            filename = self._session.credentials_file
            section = profile
        else:
            filename = self._session.config_file
            if profile == 'default':
                section = 'default'
            else:
                section = f'profile {profile}'

        self._config_writer.update_config({'__section__': section, key: value}, filename)
        return 0

    def _parse_varname(self, varname):
        if '.' not in varname:
            return (self._session.profile, varname)
        parts = varname.split('.')
        if parts[0] == 'default':
            return ('default', parts[1])
        if parts[0] == 'profile' and len(parts) >= 3:
            return (parts[1], parts[2])
        return (self._session.profile, varname)
