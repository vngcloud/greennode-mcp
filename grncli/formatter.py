from __future__ import annotations

import json
import sys
from typing import Any, TextIO


class Formatter:
    """Base formatter class."""

    def __init__(self, args):
        self._args = args

    def __call__(self, command_name: str, response: Any,
                 stream: TextIO | None = None) -> None:
        raise NotImplementedError

    def _get_stream(self, stream: TextIO | None) -> TextIO:
        return stream or sys.stdout

    def _apply_query(self, response: Any) -> Any:
        if self._args.query is not None:
            return self._args.query.search(response)
        return response


class JSONFormatter(Formatter):
    """Output as formatted JSON."""

    def __call__(self, command_name: str, response: Any,
                 stream: TextIO | None = None) -> None:
        stream = self._get_stream(stream)
        response = self._apply_query(response)
        if response != {} and response is not None:
            json.dump(response, stream, indent=4, ensure_ascii=False,
                     default=str)
            stream.write('\n')


class TextFormatter(Formatter):
    """Output as tab-separated text."""

    def __call__(self, command_name: str, response: Any,
                 stream: TextIO | None = None) -> None:
        stream = self._get_stream(stream)
        response = self._apply_query(response)
        if response is None or response == {}:
            return
        self._format(response, stream)

    def _format(self, data: Any, stream: TextIO) -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            stream.write(
                                '\t'.join(str(v) for v in item.values())
                            )
                            stream.write('\n')
                        else:
                            stream.write(str(item) + '\n')
                    return
            stream.write('\t'.join(str(v) for v in data.values()))
            stream.write('\n')
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    stream.write('\t'.join(str(v) for v in item.values()))
                    stream.write('\n')
                else:
                    stream.write(str(item) + '\n')
        else:
            stream.write(str(data) + '\n')


class TableFormatter(Formatter):
    """Output as formatted table."""

    def __call__(self, command_name: str, response: Any,
                 stream: TextIO | None = None) -> None:
        stream = self._get_stream(stream)
        response = self._apply_query(response)
        if response is None or response == {}:
            return
        self._format(response, stream)

    def _format(self, data: Any, stream: TextIO) -> None:
        rows = self._extract_rows(data)
        if not rows:
            return

        if isinstance(rows[0], dict):
            headers = list(rows[0].keys())
            str_rows = [[str(row.get(h, '')) for h in headers] for row in rows]
        else:
            headers = None
            str_rows = [[str(v)] for v in rows]

        if headers:
            col_widths = [len(h) for h in headers]
            for row in str_rows:
                for i, val in enumerate(row):
                    col_widths[i] = max(col_widths[i], len(val))

            header_line = ' | '.join(
                h.ljust(col_widths[i]) for i, h in enumerate(headers)
            )
            sep_line = '-+-'.join('-' * w for w in col_widths)

            stream.write(header_line + '\n')
            stream.write(sep_line + '\n')
            for row in str_rows:
                stream.write(
                    ' | '.join(
                        val.ljust(col_widths[i]) for i, val in enumerate(row)
                    ) + '\n'
                )

    def _extract_rows(self, data: Any) -> list:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list):
                    return value
            return [data]
        return [data]


def get_formatter(format_type: str, args) -> Formatter:
    formatters = {
        'json': JSONFormatter,
        'text': TextFormatter,
        'table': TableFormatter,
    }
    if format_type not in formatters:
        raise ValueError(f"Invalid output format: {format_type}")
    return formatters[format_type](args)
