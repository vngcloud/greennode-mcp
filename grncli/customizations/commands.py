from __future__ import annotations

import sys
from collections import OrderedDict
from typing import Any

from grncli.arguments import CustomArgument
from grncli.argparser import ArgTableArgParser
from grncli.commands import CLICommand


class BasicCommand(CLICommand):
    """Base class for hand-written commands (similar to AWS CLI BasicCommand)."""

    NAME = ''
    DESCRIPTION = ''
    ARG_TABLE: list[dict[str, Any]] = []
    SUBCOMMANDS: list[dict[str, Any]] = []

    def __init__(self, session):
        self._session = session
        self._arg_table: OrderedDict | None = None
        self._subcommand_table: OrderedDict | None = None

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def arg_table(self) -> OrderedDict:
        if self._arg_table is None:
            self._arg_table = self._build_arg_table()
        return self._arg_table

    @property
    def subcommand_table(self) -> OrderedDict:
        if self._subcommand_table is None:
            self._subcommand_table = self._build_subcommand_table()
        return self._subcommand_table

    def __call__(self, args: list[str], parsed_globals) -> int:
        self._arg_table = self._build_arg_table()
        self._subcommand_table = self._build_subcommand_table()

        # Handle help before parsing
        if args == ['help'] or args == ['--help'] or args == ['-h']:
            self._print_help()
            return 0

        parser = ArgTableArgParser(
            self._arg_table, self._subcommand_table,
            description=self.DESCRIPTION,
        )
        parsed_args, remaining = parser.parse_known_args(args)

        if getattr(parsed_args, 'subcommand', None) is not None:
            return self._subcommand_table[parsed_args.subcommand](
                remaining, parsed_globals
            )

        if remaining:
            raise ValueError(f"Unknown options: {', '.join(remaining)}")

        return self._run_main(parsed_args, parsed_globals)

    def _print_help(self) -> None:
        sys.stdout.write(f"\nDESCRIPTION\n    {self.DESCRIPTION}\n\nSYNOPSIS\n    {self.NAME}\n")

        required = []
        optional = []
        for arg_data in self.ARG_TABLE:
            name = arg_data['name']
            is_flag = arg_data.get('action') in ('store_true', 'store_false')
            is_required = arg_data.get('required', False)

            if is_flag:
                display = f"--{name}"
            else:
                display = f"--{name} <value>"

            if is_required:
                required.append((display, arg_data.get('help_text', '')))
            else:
                optional.append((display, arg_data.get('help_text', '')))

        if required:
            for display, _ in required:
                sys.stdout.write(f"      {display}\n")
        if optional:
            for display, _ in optional:
                sys.stdout.write(f"      [{display}]\n")

        sys.stdout.write("\nREQUIRED OPTIONS\n")
        if required:
            for display, help_text in required:
                sys.stdout.write(f"    {display}\n")
                if help_text:
                    sys.stdout.write(f"        {help_text}\n\n")
        else:
            sys.stdout.write("    None\n\n")

        sys.stdout.write("OPTIONAL OPTIONS\n")
        if optional:
            for display, help_text in optional:
                sys.stdout.write(f"    {display}\n")
                if help_text:
                    sys.stdout.write(f"        {help_text}\n\n")
        else:
            sys.stdout.write("    None\n\n")

    def _run_main(self, parsed_args, parsed_globals) -> int:
        raise NotImplementedError

    def _build_arg_table(self) -> OrderedDict:
        arg_table = OrderedDict()
        for arg_data in self.ARG_TABLE:
            data = dict(arg_data)
            custom_arg = CustomArgument(**data)
            arg_table[data['name']] = custom_arg
        return arg_table

    def _build_subcommand_table(self) -> OrderedDict:
        table = OrderedDict()
        for sub in self.SUBCOMMANDS:
            table[sub['name']] = sub['command_class'](self._session)
        return table

    @classmethod
    def add_command(cls, command_table, session, **kwargs):
        command_table[cls.NAME] = cls(session)


def display_output(response, parsed_globals):
    """Format and display API response based on --output flag."""
    from grncli.formatter import get_formatter
    output_format = getattr(parsed_globals, 'output', 'json') or 'json'
    formatter = get_formatter(output_format, parsed_globals)
    formatter('', response)
