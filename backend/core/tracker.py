"""Target Tracker — simulated track maintenance after a confirmed threat.

Once fusion confirms a credible aerial threat (high/critical, fused), the
tracker opens a track and emits periodic `track_update` events: bearing drifts,
range closes at the scenario's closing speed, and track confidence ramps. This
feeds the operator's tracking overlay. Real hardware would replace this with a
DOA estimator + tracker; the event shape stays identical.
"""

from __future__ import annotations

import asyncio
import logging
import math
from typing import Callable, Optional

from core.event_bus import EventBus
from core.state import SystemState
from models import TrackUpdate, new_id

log = logging.getLogger("core.tracker")

TrackPlanProvider = Callable[[], Optional[dict]]

CONFIRMED_LEVELS = {"high", "critical"}
TICK_S = 1.0
MIN_RANGE_M = 40.0


class Tracker:
    def __init__(self, bus: EventBus, state: SystemState,
                 track_plan_provider: Optional[TrackPlanProvider] = None) -> None:
        self.bus = bus
        self.state = state
        self._track_plan_provider = track_plan_provider
        self._consume_task: asyncio.Task | None = None
        self._track_task: asyncio.Task | None = None

    def start(self) -> None:
        self._consume_task = asyncio.create_task(self._consume())

    async def stop(self) -> None:
        for task in (self._consume_task, self._track_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._consume_task = None
        self._track_task = None

    def reset(self) -> None:
        if self._track_task and not self._track_task.done():
            self._track_task.cancel()
        self._track_task = None

    async def _consume(self) -> None:
        async for payload in self.bus.stream("fused_assessment"):
            level = payload.get("threat_level")
            source = payload.get("source_mode")
            already = self._track_task and not self._track_task.done()
            if level in CONFIRMED_LEVELS and source == "fused" and not already:
                self._track_task = asyncio.create_task(self._track_loop())

    async def _track_loop(self) -> None:
        plan = self._track_plan_provider() if self._track_plan_provider else None
        plan = plan or {}
        bearing = float(plan.get("initial_bearing_deg", 0.0))
        rng = float(plan.get("initial_range_m", 400.0))
        speed = float(plan.get("closing_speed_mps", 12.0))
        track_id = f"trk-{new_id()[:8]}"

        self.state.subsystems["tracking"] = "active"
        log.info("track %s opened: bearing=%.0f range=%.0fm", track_id, bearing, rng)
        tick = 0
        try:
            while rng > MIN_RANGE_M:
                state = "acquiring" if tick == 0 else "tracking"
                conf = min(0.95, 0.55 + 0.06 * tick)
                update = TrackUpdate(
                    track_id=track_id, state=state,  # type: ignore[arg-type]
                    bearing_deg=round(bearing % 360, 1),
                    range_m=round(rng, 1),
                    speed_mps=round(speed, 1),
                    confidence=round(conf, 3),
                )
                await self.bus.publish("track_update", update.model_dump())
                if self.state.tracking is not None:
                    self.state.tracking.track_id = track_id
                    self.state.tracking.state = update.state
                    self.state.tracking.bearing_deg = update.bearing_deg
                    self.state.tracking.range_m = update.range_m
                    self.state.tracking.speed_mps = update.speed_mps
                    self.state.tracking.confidence = update.confidence

                await asyncio.sleep(TICK_S)
                # Closing target: range decreases, bearing drifts smoothly.
                rng = max(MIN_RANGE_M, rng - speed * TICK_S)
                bearing += 2.5 * math.sin(tick * 0.6)
                tick += 1

            # Target closed to minimum range and passed — track is lost.
            lost = TrackUpdate(
                track_id=track_id, state="lost",
                bearing_deg=round(bearing % 360, 1),
                range_m=round(rng, 1), speed_mps=round(speed, 1),
                confidence=0.4,
            )
            await self.bus.publish("track_update", lost.model_dump())
            if self.state.tracking is not None:
                self.state.tracking.state = "lost"
                self.state.tracking.confidence = 0.4
            log.info("track %s lost at close range (%.0fm)", track_id, rng)
        except asyncio.CancelledError:
            log.info("track %s terminated", track_id)
            raise
