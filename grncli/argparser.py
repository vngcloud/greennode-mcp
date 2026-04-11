# greenode-cli/grncli/argparser.py
from __future__ import annotations

import argparse
from collections import OrderedDict
from difflib import get_close_matches
from typing import Any

USAGE = "grn [options] <command> <subcommand> [parameters]"


class CommandAction(argparse.Action):
    """Custom argparse action for dynamic command choices."""

    def __init__(self, option_strings, dest, command_table, **kwargs):
        self.command_table = command_table
        super().__init__(option_strings, dest, choices=self.choices, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

    @property
    def choices(self):
        return list(self.command_table.keys())

    @choices.setter
    def choices(self, val):
        pass


class CLIArgParser(argparse.ArgumentParser):
    """Base parser with custom error handling."""

    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault('formatter_class', argparse.RawTextHelpFormatter)
        kwargs.setdefault('add_help', False)
        kwargs.setdefault('conflict_handler', 'resolve')
        super().__init__(*args, **kwargs)

    def _check_value(self, action, value):
        if action.choices is not None and value not in action.choices:
            msg = [f'Invalid command: {value}\n\nAvailable commands:\n']
            for choice in action.choices:
                msg.append(f'  {choice}')
            possible = get_close_matches(value, action.choices, cutoff=0.8)
            if possible:
                msg.append(f'\n\nDid you mean: {", ".join(possible)}?')
            raise argparse.ArgumentError(action, '\n'.join(msg))


class MainArgParser(CLIArgParser):
    """Top-level parser: global args + command selection."""

    def __init__(
        self,
        command_table: OrderedDict,
        version_string: str,
        description: str,
        argument_table: OrderedDict,
        prog: str = 'grn',
    ):
        super().__init__(description=description, usage=USAGE, prog=prog)
        self._build(command_table, version_string, argument_table)

    def _build(self, command_table, version_string, argument_table):
        for argument in argument_table.values():
            argument.add_to_parser(self)
        self.add_argument(
            '--version', action='version', version=version_string
        )
        self.add_argument('command', action=CommandAction,
                         command_table=command_table)


class ServiceArgParser(CLIArgParser):
    """Service-level parser: operation selection."""

    def __init__(self, operations_table: OrderedDict, service_name: str):
        super().__init__(usage=USAGE)
        self._service_name = service_name
        self.add_argument('operation', action=CommandAction,
                         command_table=operations_table)


class ArgTableArgParser(CLIArgParser):
    """Operation-level parser: parse specific arguments."""

    def __init__(
        self,
        argument_table: OrderedDict,
        command_table: OrderedDict | None = None,
        description: str = '',
    ):
        super().__init__(usage=USAGE, add_help=True, description=description)
        for argument in argument_table.values():
            argument.add_to_parser(self)
        if command_table:
            self.add_argument(
                'subcommand', action=CommandAction,
                command_table=command_table, nargs='?',
            )
