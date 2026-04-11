from __future__ import annotations

import io
import json
from argparse import Namespace

from grncli.formatter import JSONFormatter, TableFormatter, TextFormatter, get_formatter


class TestJSONFormatter:
    def test_format_dict(self):
        stream = io.StringIO()
        args = Namespace(query=None, color='off')
        formatter = JSONFormatter(args)
        formatter("test", {"name": "my-cluster", "status": "ACTIVE"}, stream)
        output = stream.getvalue()
        data = json.loads(output)
        assert data["name"] == "my-cluster"

    def test_format_with_jmespath_query(self):
        stream = io.StringIO()
        import jmespath
        args = Namespace(query=jmespath.compile("items[].name"), color='off')
        formatter = JSONFormatter(args)
        formatter(
            "test",
            {"items": [{"name": "a"}, {"name": "b"}]},
            stream,
        )
        output = stream.getvalue()
        data = json.loads(output)
        assert data == ["a", "b"]

    def test_empty_response(self):
        stream = io.StringIO()
        args = Namespace(query=None, color='off')
        formatter = JSONFormatter(args)
        formatter("test", {}, stream)
        assert stream.getvalue() == ""


class TestTextFormatter:
    def test_format_flat_dict(self):
        stream = io.StringIO()
        args = Namespace(query=None, color='off')
        formatter = TextFormatter(args)
        formatter("test", {"id": "abc", "name": "cluster1"}, stream)
        output = stream.getvalue()
        assert "abc" in output
        assert "cluster1" in output

    def test_format_list(self):
        stream = io.StringIO()
        args = Namespace(query=None, color='off')
        formatter = TextFormatter(args)
        formatter("test", {"items": [{"id": "a"}, {"id": "b"}]}, stream)
        output = stream.getvalue()
        assert "a" in output
        assert "b" in output


class TestTableFormatter:
    def test_format_list_of_dicts(self):
        stream = io.StringIO()
        args = Namespace(query=None, color='off')
        formatter = TableFormatter(args)
        formatter(
            "test",
            {"items": [
                {"id": "abc", "name": "cluster1"},
                {"id": "def", "name": "cluster2"},
            ]},
            stream,
        )
        output = stream.getvalue()
        assert "cluster1" in output
        assert "cluster2" in output


class TestGetFormatter:
    def test_json(self):
        args = Namespace(query=None, color='off')
        assert isinstance(get_formatter('json', args), JSONFormatter)

    def test_text(self):
        args = Namespace(query=None, color='off')
        assert isinstance(get_formatter('text', args), TextFormatter)

    def test_table(self):
        args = Namespace(query=None, color='off')
        assert isinstance(get_formatter('table', args), TableFormatter)

    def test_unknown_raises(self):
        args = Namespace(query=None, color='off')
        try:
            get_formatter('xml', args)
            assert False, "Should have raised"
        except ValueError:
            pass
