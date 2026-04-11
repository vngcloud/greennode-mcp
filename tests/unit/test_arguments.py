from __future__ import annotations

import argparse
from collections import OrderedDict

from grncli.arguments import BaseCLIArgument, CustomArgument
from grncli.argparser import MainArgParser, ServiceArgParser, ArgTableArgParser


class TestCustomArgument:
    def test_basic_properties(self):
        arg = CustomArgument(name='region', help_text='The region')
        assert arg.name == 'region'
        assert arg.cli_name == '--region'
        assert arg.py_name == 'region'

    def test_hyphenated_name(self):
        arg = CustomArgument(name='cluster-id', help_text='Cluster ID')
        assert arg.cli_name == '--cluster-id'
        assert arg.py_name == 'cluster_id'

    def test_add_to_arg_table(self):
        arg = CustomArgument(name='region', help_text='Region')
        table = OrderedDict()
        arg.add_to_arg_table(table)
        assert 'region' in table
        assert table['region'] is arg

    def test_add_to_parser(self):
        arg = CustomArgument(name='output', choices=['json', 'text', 'table'])
        parser = argparse.ArgumentParser()
        arg.add_to_parser(parser)
        result = parser.parse_args(['--output', 'json'])
        assert result.output == 'json'

    def test_boolean_argument(self):
        arg = CustomArgument(
            name='debug', action='store_true', default=False
        )
        parser = argparse.ArgumentParser()
        arg.add_to_parser(parser)
        result = parser.parse_args(['--debug'])
        assert result.debug is True

    def test_positional_argument(self):
        arg = CustomArgument(
            name='varname', positional_arg=True, help_text='Variable name'
        )
        parser = argparse.ArgumentParser()
        arg.add_to_parser(parser)
        result = parser.parse_args(['region'])
        assert result.varname == 'region'


class TestMainArgParser:
    def test_parse_command(self):
        command_table = OrderedDict([('vks', None), ('configure', None)])
        arg_table = OrderedDict()
        parser = MainArgParser(
            command_table, '0.1.0', 'Greenode CLI', arg_table, prog='grn'
        )
        parsed, remaining = parser.parse_known_args(['vks'])
        assert parsed.command == 'vks'

    def test_parse_global_args(self):
        command_table = OrderedDict([('vks', None)])
        region_arg = CustomArgument(name='region', help_text='Region')
        arg_table = OrderedDict()
        region_arg.add_to_arg_table(arg_table)
        parser = MainArgParser(
            command_table, '0.1.0', 'Greenode CLI', arg_table, prog='grn'
        )
        parsed, remaining = parser.parse_known_args(
            ['--region', 'HAN', 'vks']
        )
        assert parsed.region == 'HAN'
        assert parsed.command == 'vks'


class TestServiceArgParser:
    def test_parse_operation(self):
        ops_table = OrderedDict([
            ('list-clusters', None),
            ('get-cluster', None),
        ])
        parser = ServiceArgParser(ops_table, 'vks')
        parsed, remaining = parser.parse_known_args(['list-clusters'])
        assert parsed.operation == 'list-clusters'


class TestArgTableArgParser:
    def test_parse_args(self):
        arg_table = OrderedDict()
        CustomArgument(
            name='cluster-id', help_text='Cluster ID'
        ).add_to_arg_table(arg_table)
        parser = ArgTableArgParser(arg_table)
        parsed, remaining = parser.parse_known_args(
            ['--cluster-id', 'abc-123']
        )
        assert parsed.cluster_id == 'abc-123'
