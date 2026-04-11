# greenode-cli/grncli/customizations/configure/__init__.py
from __future__ import annotations


def register_configure_cmd(event_hooks):
    event_hooks.register(
        'building-command-table.main',
        _inject_configure,
    )


def _inject_configure(command_table, session, **kwargs):
    from grncli.customizations.configure.configure import ConfigureCommand
    command_table['configure'] = ConfigureCommand(session)
