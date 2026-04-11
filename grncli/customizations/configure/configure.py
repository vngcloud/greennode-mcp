# greenode-cli/grncli/customizations/configure/configure.py
from __future__ import annotations

from grncli.customizations.commands import BasicCommand
from grncli.customizations.configure.writer import ConfigFileWriter


class InteractivePrompter:
    VALID_REGIONS = {'HCM-3', 'HAN'}
    VALID_OUTPUTS = {'json', 'text', 'table'}

    VALIDATORS = {
        'region': lambda v: v in InteractivePrompter.VALID_REGIONS,
        'output': lambda v: v in InteractivePrompter.VALID_OUTPUTS,
    }

    def get_value(self, current_value, config_name, prompt_text,
                  default=None):
        # Use current value for display, but fall back to default
        # if current value is invalid
        validator = self.VALIDATORS.get(config_name)
        current_is_valid = (
            current_value and (not validator or validator(current_value))
        )

        if current_is_valid:
            if config_name in ('client_id', 'client_secret'):
                display = '*' * 16 + current_value[-4:]
            else:
                display = current_value
        elif default:
            display = default
        else:
            display = 'None'

        response = input(f'{prompt_text} [{display}]: ')
        if not response:
            if current_is_valid:
                return None  # Keep current value
            if default:
                return default  # Reset to default
            return None
        return response


class ConfigureCommand(BasicCommand):
    NAME = 'configure'
    DESCRIPTION = 'Configure credentials and settings for Greenode CLI'

    SUBCOMMANDS = []  # Set in __init__

    VALUES_TO_PROMPT = [
        ('client_id', 'GRN Client ID'),
        ('client_secret', 'GRN Client Secret'),
        ('region', 'Default region name'),
        ('output', 'Default output format'),
    ]

    # Default values used when no current value exists and user presses Enter
    DEFAULTS = {
        'region': 'HCM-3',
        'output': 'json',
    }

    CREDS_KEYS = {'client_id', 'client_secret'}

    def __init__(self, session, prompter=None, config_writer=None):
        super().__init__(session)
        self._prompter = prompter or InteractivePrompter()
        self._config_writer = config_writer or ConfigFileWriter()
        from grncli.customizations.configure.list import ConfigureListCommand
        from grncli.customizations.configure.get import ConfigureGetCommand
        from grncli.customizations.configure.set import ConfigureSetCommand
        self.SUBCOMMANDS = [
            {'name': 'list', 'command_class': ConfigureListCommand},
            {'name': 'get', 'command_class': ConfigureGetCommand},
            {'name': 'set', 'command_class': ConfigureSetCommand},
        ]

    def _run_main(self, parsed_args, parsed_globals):
        try:
            creds = self._session.get_credentials()
        except Exception:
            creds = {}
        try:
            config = self._session.get_scoped_config()
        except Exception:
            config = {}

        current = {**creds, **config}
        new_creds = {}
        new_config = {}

        for config_name, prompt_text in self.VALUES_TO_PROMPT:
            current_value = current.get(config_name)
            default = self.DEFAULTS.get(config_name)
            new_value = self._prompter.get_value(
                current_value, config_name, prompt_text, default=default,
            )
            if new_value is not None:
                if config_name in self.CREDS_KEYS:
                    new_creds[config_name] = new_value
                else:
                    new_config[config_name] = new_value

        profile = getattr(parsed_globals, 'profile', None) or self._session.profile

        if new_creds:
            section = profile if profile != 'default' else 'default'
            new_creds['__section__'] = section
            self._config_writer.update_config(new_creds, self._session.credentials_file)

        if new_config:
            if profile and profile != 'default':
                section = f'profile {profile}'
            else:
                section = 'default'
            new_config['__section__'] = section
            self._config_writer.update_config(new_config, self._session.config_file)

        return 0
