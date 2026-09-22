"""In-process event bus (spec section 37).

Stands in for Kafka/Event Hub/PubSub in the POC: same event names, same
payload shapes, dispatched synchronously in-process instead of through a
broker. A production deployment would replace `publish()`'s body with a
topic produce call and let independent consumer groups (extraction
workers, classification workers, embedding workers, ...) scale
independently — see docs/scaling.md. Nothing upstream of this module would
need to change.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

Handler = Callable[[dict], None]


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: dict) -> None:
        for handler in self._subscribers.get(event_type, []):
            handler(payload)


_bus = EventBus()


def get_event_bus() -> EventBus:
    return _bus
