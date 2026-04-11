from __future__ import annotations

from grncli.emitter import HierarchicalEmitter


class TestHierarchicalEmitter:
    def test_register_and_emit(self):
        emitter = HierarchicalEmitter()
        calls = []
        emitter.register('my-event', lambda **kwargs: calls.append(kwargs))
        emitter.emit('my-event', arg1='val1')
        assert len(calls) == 1
        assert calls[0]['arg1'] == 'val1'

    def test_hierarchical_matching(self):
        emitter = HierarchicalEmitter()
        calls = []
        emitter.register('building-command-table.vks',
                         lambda **kwargs: calls.append('vks'))
        emitter.emit('building-command-table.vks')
        assert calls == ['vks']

    def test_no_match(self):
        emitter = HierarchicalEmitter()
        calls = []
        emitter.register('event-a', lambda **kwargs: calls.append('a'))
        emitter.emit('event-b')
        assert calls == []

    def test_emit_first_non_none(self):
        emitter = HierarchicalEmitter()
        emitter.register('my-event', lambda **kwargs: None)
        emitter.register('my-event', lambda **kwargs: 'result')
        result = emitter.emit_first_non_none('my-event')
        assert result == 'result'

    def test_emit_first_non_none_all_none(self):
        emitter = HierarchicalEmitter()
        emitter.register('my-event', lambda **kwargs: None)
        result = emitter.emit_first_non_none('my-event')
        assert result is None

    def test_multiple_handlers_same_event(self):
        emitter = HierarchicalEmitter()
        results = []
        emitter.register('ev', lambda **kwargs: results.append('first'))
        emitter.register('ev', lambda **kwargs: results.append('second'))
        emitter.emit('ev')
        assert results == ['first', 'second']
