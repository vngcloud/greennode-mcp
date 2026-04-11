# greenode-cli/grncli/clidriver.py
from __future__ import annotations

import json
import logging
import os
import platform
import sys
from collections import OrderedDict
from typing import Any

import jmespath

import grncli
from grncli.arguments import CustomArgument
from grncli.argparser import MainArgParser, ServiceArgParser
from grncli.commands import CLICommand
from grncli.formatter import get_formatter
from grncli.plugin import load_plugins
from grncli.session import Session

LOG = logging.getLogger(__name__)


def main(args: list[str] | None = None) -> int:
    driver = create_clidriver()
    return driver.main(args)


def create_clidriver() -> CLIDriver:
    session = Session()
    load_plugins({}, event_hooks=session.emitter)
    return CLIDriver(session=session)


class CLIDriver:
    """Main CLI orchestrator (similar to AWS CLI CLIDriver)."""

    def __init__(self, session: Session):
        self.session = session
        self._cli_data: dict | None = None
        self._command_table: OrderedDict | None = None
        self._argument_table: OrderedDict | None = None

    def main(self, args: list[str] | None = None) -> int:
        if args is None:
            args = sys.argv[1:]

        try:
            return self._do_main(args)
        except KeyboardInterrupt:
            sys.stdout.write('\n')
            return 130
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            LOG.debug("Exception", exc_info=True)
            return 255

    def _do_main(self, args: list[str]) -> int:
        import argparse

        command_table = self._get_command_table()
        argument_table = self._get_argument_table()

        # Handle no args or 'help' command
        if not args or args == ['help']:
            self._print_usage(command_table)
            return 0

        version_string = (
            f"grn-cli/{grncli.__version__} "
            f"Python/{platform.python_version()} "
            f"{platform.system()}/{platform.release()}"
        )

        parser = MainArgParser(
            command_table,
            version_string,
            self._get_cli_data().get('description', ''),
            argument_table,
            prog='grn',
        )

        try:
            parsed_args, remaining = parser.parse_known_args(args)
        except SystemExit as e:
            if e.code == 0:
                raise
            return 255
        except argparse.ArgumentError:
            return 255

        self._handle_top_level_args(parsed_args)

        command_name = getattr(parsed_args, 'command', None)
        if not command_name or command_name not in command_table:
            return 255

        return command_table[command_name](remaining, parsed_args)

    def _print_usage(self, command_table: OrderedDict) -> None:
        cli_data = self._get_cli_data()
        sys.stdout.write(
            f"\nusage: {cli_data.get('synopsis', 'grn [options] <command> <subcommand> [parameters]')}\n\n"
        )
        sys.stdout.write(f"{cli_data.get('description', '')}\n\n")
        if cli_data.get('help_usage'):
            sys.stdout.write(f"{cli_data['help_usage']}\n\n")

        # Command descriptions
        command_help = {
            'configure': 'Configure credentials and settings',
            'vks': 'VKS (VNG Kubernetes Service) commands',
        }

        sys.stdout.write("Available commands:\n\n")
        for cmd_name in command_table:
            desc = command_help.get(cmd_name, '')
            sys.stdout.write(f"  {cmd_name:<16s}{desc}\n")
        sys.stdout.write('\n')

    def _get_cli_data(self) -> dict:
        if self._cli_data is None:
            cli_json_path = os.path.join(grncli._grncli_data_path, 'cli.json')
            with open(cli_json_path) as f:
                self._cli_data = json.load(f)
        return self._cli_data

    def _get_command_table(self) -> OrderedDict:
        if self._command_table is None:
            self._command_table = self._build_command_table()
        return self._command_table

    def _build_command_table(self) -> OrderedDict:
        command_table = OrderedDict()
        self.session.emit(
            'building-command-table.main',
            command_table=command_table,
            session=self.session,
        )
        return command_table

    def _get_argument_table(self) -> OrderedDict:
        if self._argument_table is None:
            self._argument_table = self._build_argument_table()
        return self._argument_table

    def _build_argument_table(self) -> OrderedDict:
        argument_table = OrderedDict()
        cli_data = self._get_cli_data()
        for option_name, option_params in cli_data.get('options', {}).items():
            params = dict(option_params)
            params['name'] = option_name
            if 'help' in params:
                params['help_text'] = params.pop('help')
            arg = CustomArgument(**params)
            arg.add_to_arg_table(argument_table)
        return argument_table

    def _handle_top_level_args(self, parsed_args) -> None:
        if getattr(parsed_args, 'debug', False):
            logging.basicConfig(level=logging.DEBUG)

        if getattr(parsed_args, 'profile', None):
            self.session.profile = parsed_args.profile

        if getattr(parsed_args, 'region', None):
            self.session.set_region_override(parsed_args.region)

        if getattr(parsed_args, 'endpoint_url', None):
            self.session.set_endpoint_override(parsed_args.endpoint_url)

        # SSL verification
        verify_ssl = getattr(parsed_args, 'verify_ssl', None)
        if verify_ssl is not None:
            self.session.verify_ssl = verify_ssl
            if not verify_ssl:
                sys.stderr.write(
                    "Warning: SSL certificate verification is disabled. "
                    "This is insecure and should only be used for testing.\n"
                )

        # Timeouts
        read_timeout = getattr(parsed_args, 'read_timeout', None)
        connect_timeout = getattr(parsed_args, 'connect_timeout', None)
        if read_timeout is not None or connect_timeout is not None:
            self.session.set_timeouts(
                read=read_timeout,
                connect=connect_timeout,
            )

        query_str = getattr(parsed_args, 'query', None)
        if query_str:
            parsed_args.query = jmespath.compile(query_str)
        else:
            parsed_args.query = None

        if not getattr(parsed_args, 'output', None):
            parsed_args.output = self.session.get_config_variable('output') or 'json'


class ServiceCommand(CLICommand):
    """Represents a service (e.g., 'grn vks ...')."""

    def __init__(self, name: str, session: Session):
        self._name = name
        self._session = session
        self._command_table: OrderedDict | None = None

    @property
    def name(self) -> str:
        return self._name

    def __call__(self, args: list[str], parsed_globals) -> int:
        command_table = self._get_command_table()

        if not args or args == ['help']:
            self._print_usage(command_table)
            return 0

        parser = ServiceArgParser(command_table, self._name)
        parsed_args, remaining = parser.parse_known_args(args)
        return command_table[parsed_args.operation](remaining, parsed_globals)

    def _print_usage(self, command_table: OrderedDict) -> None:
        sys.stdout.write(f"\nusage: grn {self._name} <command> [parameters]\n\n")
        sys.stdout.write("Available commands:\n\n")
        for cmd_name in command_table:
            desc = command_table[cmd_name].DESCRIPTION if hasattr(command_table[cmd_name], 'DESCRIPTION') else ''
            sys.stdout.write(f"  {cmd_name:<24s}{desc}\n")
        sys.stdout.write('\n')

    def _get_command_table(self) -> OrderedDict:
        if self._command_table is None:
            self._command_table = OrderedDict()
            self._session.emit(
                f'building-command-table.{self._name}',
                command_table=self._command_table,
                session=self._session,
            )
        return self._command_table
