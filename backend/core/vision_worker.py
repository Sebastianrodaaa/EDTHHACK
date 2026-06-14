"""Vision Worker — consumes VisionRequests, drives the vision adapter.

Subscribes to `vision_request` on the bus. For each request it marks the vision
subsystem active, calls the adapter under a hard timeout (so a slow/dead CV
model degrades gracefully instead of hanging the cascade), and publishes either
a `vision_event` or a `vision_timeout`.
"""

from __future__ import annotations

import asyncio
import logging

import config
from adapters.vision import VisionAdapter
from core.event_bus import EventBus
from core.state import SystemState
from models import VisionRequest, VisionTimeout

log = logging.getLogger("core.vision_worker")


class VisionWorker:
    def __init__(
        self, bus: EventBus, adapter: VisionAdapter, state: SystemState
    ) -> None:
        self.bus = bus
        self.adapter = adapter
        self.state = state
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        async for payload in self.bus.stream("vision_request"):
            request = VisionRequest(**payload)
            await self._process(request)

    async def _process(self, request: VisionRequest) -> None:
        self.state.subsystems["vision"] = "active"
        log.info(
            "vision_request received (trigger=%s, acoustic_conf=%.2f) — analysing",
            request.trigger_acoustic_id,
            request.acoustic_confidence,
        )
        try:
            event = await asyncio.wait_for(
                self.adapter.analyze(request), timeout=config.VISION_TIMEOUT_S
            )
        except asyncio.TimeoutError:
            log.warning("vision analysis timed out after %.1fs", config.VISION_TIMEOUT_S)
            self.state.subsystems["vision"] = "degraded"
            await self.bus.publish(
                "vision_timeout",
                VisionTimeout(
                    trigger_acoustic_id=request.trigger_acoustic_id,
                    timeout_s=config.VISION_TIMEOUT_S,
                ).model_dump(),
            )
            return

        self.state.subsystems["vision"] = "online"
        log.info(
            "vision_event: class=%s conf=%.2f bbox=%s",
            event.classification,
            event.confidence,
            "yes" if event.bounding_box else "none",
        )
        await self.bus.publish("vision_event", event.model_dump())
