from __future__ import annotations

from argparse import Namespace
from collections import OrderedDict
from unittest.mock import MagicMock

from grncli.customizations.commands import BasicCommand


class DummyCommand(BasicCommand):
    NAME = 'dummy'
    DESCRIPTION = 'A dummy command'
    ARG_TABLE = [
        {'name': 'name', 'help_text': 'The name'},
        {'name': 'count', 'help_text': 'Count', 'default': '10'},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        self.last_args = parsed_args
        return 0


class DummySubcommand(BasicCommand):
    NAME = 'sub'
    DESCRIPTION = 'A subcommand'
    ARG_TABLE = []

    def _run_main(self, parsed_args, parsed_globals):
        return 42


class ParentCommand(BasicCommand):
    NAME = 'parent'
    DESCRIPTION = 'Parent with subcommands'
    SUBCOMMANDS = [
        {'name': 'sub', 'command_class': DummySubcommand},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        return 0


class TestBasicCommand:
    def test_call_with_args(self):
        session = MagicMock()
        cmd = DummyCommand(session)
        parsed_globals = Namespace(region=None, output=None, profile=None)
        rc = cmd(['--name', 'test-value'], parsed_globals)
        assert rc == 0
        assert cmd.last_args.name == 'test-value'

    def test_default_values(self):
        session = MagicMock()
        cmd = DummyCommand(session)
        parsed_globals = Namespace(region=None, output=None, profile=None)
        cmd(['--name', 'x'], parsed_globals)
        assert cmd.last_args.count == '10'

    def test_subcommand_dispatch(self):
        session = MagicMock()
        cmd = ParentCommand(session)
        parsed_globals = Namespace(region=None, output=None, profile=None)
        rc = cmd(['sub'], parsed_globals)
        assert rc == 42

    def test_add_command_class_method(self):
        session = MagicMock()
        table = OrderedDict()
        DummyCommand.add_command(table, session)
        assert 'dummy' in table
        assert isinstance(table['dummy'], DummyCommand)

    def test_name_property(self):
        session = MagicMock()
        cmd = DummyCommand(session)
        assert cmd.name == 'dummy'
