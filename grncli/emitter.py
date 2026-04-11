from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class HierarchicalEmitter:
    """Simple event emitter with hierarchical event names.
    Modeled after botocore's HierarchicalEmitter but simplified.
    Events are matched by exact name (no wildcard support needed for v1).
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def register(self, event_name: str, handler: Callable) -> None:
        self._handlers[event_name].append(handler)

    def emit(self, event_name: str, **kwargs: Any) -> list[Any]:
        responses = []
        for handler in self._handlers.get(event_name, []):
            response = handler(**kwargs)
            responses.append(response)
        return responses

    def emit_first_non_none(self, event_name: str, **kwargs: Any) -> Any:
        for handler in self._handlers.get(event_name, []):
            response = handler(**kwargs)
            if response is not None:
                return response
        return None
