"""Acoustic Node — detection threshold + temporal gating.

Consumes AcousticEvents, publishes every event to the bus (for the operator
orb/feed), and decides when a sustained drone-like signature warrants a
VisionRequest. Temporal gating (N consecutive frames) plus a cooldown suppress
single-frame false positives and request storms.
"""

from __future__ import annotations

import time

import config
from core.event_bus import EventBus
from models import AcousticEvent, VisionRequest


class AcousticNode:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._consecutive = 0
        self._last_trigger_ts = 0.0

    async def handle(self, event: AcousticEvent) -> None:
        # Always surface the raw acoustic event.
        await self.bus.publish("acoustic_event", event.model_dump())

        is_hot = (
            event.classification == "drone_like"
            and event.confidence >= config.ACOUSTIC_CONF_THRESHOLD
        )
        if is_hot:
            self._consecutive += 1
        else:
            self._consecutive = 0

        if self._consecutive >= config.ACOUSTIC_GATE_FRAMES and self._cooldown_ok():
            self._last_trigger_ts = time.monotonic()
            self._consecutive = 0
            request = VisionRequest(
                trigger_acoustic_id=event.id,
                acoustic_confidence=event.confidence,
            )
            await self.bus.publish("vision_request", request.model_dump())

    def _cooldown_ok(self) -> bool:
        return (
            time.monotonic() - self._last_trigger_ts
            >= config.ACOUSTIC_TRIGGER_COOLDOWN_S
        )
