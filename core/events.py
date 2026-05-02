from __future__ import annotations
import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    """Lightweight in-process async event bus.

    Stages publish events (e.g. job.completed, job.failed) and any subscriber
    that called subscribe() receives them. Handlers run concurrently via
    asyncio.gather — a failed handler is logged but does not abort others.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a coroutine handler for the given event type."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type] = [
            h for h in self._handlers[event_type] if h is not handler
        ]

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Fire all handlers registered for event_type concurrently."""
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            return
        results = await asyncio.gather(
            *(h(payload) for h in handlers), return_exceptions=True
        )
        for r in results:
            if isinstance(r, Exception):
                import logging
                logging.getLogger(__name__).error(
                    "event_handler_error event=%s error=%s", event_type, r
                )


_bus = EventBus()


def get_event_bus() -> EventBus:
    """Return the application-scoped event bus singleton."""
    return _bus
