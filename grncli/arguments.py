# greenode-cli/grncli/arguments.py
from __future__ import annotations

import argparse
from collections import OrderedDict
from typing import Any


class BaseCLIArgument:
    """Base class for all CLI arguments."""

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def cli_name(self) -> str:
        return '--' + self._name

    @property
    def py_name(self) -> str:
        return self._name.replace('-', '_')

    def add_to_arg_table(self, argument_table: OrderedDict) -> None:
        argument_table[self.name] = self

    def add_to_parser(self, parser: argparse.ArgumentParser) -> None:
        raise NotImplementedError


class CustomArgument(BaseCLIArgument):
    """Configurable argument for top-level and custom command args."""

    TYPE_MAP = {
        'int': int,
        'float': float,
        'str': str,
    }

    def __init__(
        self,
        name: str,
        help_text: str = '',
        dest: str | None = None,
        default: Any = None,
        action: str | None = None,
        required: bool | None = None,
        choices: list[str] | None = None,
        nargs: str | int | None = None,
        positional_arg: bool = False,
        type: str | None = None,
    ):
        super().__init__(name)
        self._help = help_text
        self._dest = dest
        self._default = default
        self._action = action
        self._required = required
        self._choices = choices
        self._nargs = nargs
        self._positional_arg = positional_arg
        self._type = self.TYPE_MAP.get(type) if type else None

    @property
    def cli_name(self) -> str:
        if self._positional_arg:
            return self._name
        return '--' + self._name

    def add_to_parser(self, parser: argparse.ArgumentParser) -> None:
        kwargs: dict[str, Any] = {}
        if self._help:
            kwargs['help'] = self._help
        if self._dest is not None:
            kwargs['dest'] = self._dest
        if self._default is not None:
            kwargs['default'] = self._default
        if self._action is not None:
            kwargs['action'] = self._action
        if self._choices is not None:
            kwargs['choices'] = self._choices
        if self._required is not None and not self._positional_arg:
            kwargs['required'] = self._required
        if self._nargs is not None:
            kwargs['nargs'] = self._nargs
        if self._type is not None and self._action is None:
            kwargs['type'] = self._type

        parser.add_argument(self.cli_name, **kwargs)
