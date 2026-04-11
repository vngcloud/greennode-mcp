# greenode-cli/grncli/commands.py
from __future__ import annotations


class CLICommand:
    """Interface all commands must implement."""

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def lineage(self) -> list[CLICommand]:
        return [self]

    @property
    def lineage_names(self) -> list[str]:
        return [cmd.name for cmd in self.lineage]

    def __call__(self, args: list[str], parsed_globals) -> int:
        raise NotImplementedError

    @property
    def arg_table(self) -> dict:
        return {}
