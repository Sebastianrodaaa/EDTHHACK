"""Lightweight in-process async pub/sub bus.

All backend components run in one Python process for the demo, so a set of
asyncio queues is enough — no Kafka/Redis. Each event type gets its own
broadcast fan-out; subscribers receive every message published after they
subscribe.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import AsyncIterator


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, event_type: str, maxsize: int = 0) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._subscribers[event_type].append(q)
        return q

    def unsubscribe(self, event_type: str, q: asyncio.Queue) -> None:
        if q in self._subscribers.get(event_type, []):
            self._subscribers[event_type].remove(q)

    async def publish(self, event_type: str, payload: dict) -> None:
        for q in list(self._subscribers.get(event_type, [])):
            await q.put(payload)

    async def stream(self, event_type: str) -> AsyncIterator[dict]:
        q = self.subscribe(event_type)
        try:
            while True:
                yield await q.get()
        finally:
            self.unsubscribe(event_type, q)
