"""Scenario engine — drives the repeatable end-to-end demo.

Owns event *timing*. Reads a scenario's acoustic timeline, asks the acoustic
adapter to synthesise each frame's features, and feeds the resulting events
into the Acoustic Node. The scenario's `vision` plan is exposed for the Vision
Worker's adapter to consume on each VisionRequest (Phase 2).
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from adapters.acoustic import AcousticAdapter, AcousticProfile
from core.acoustic_node import AcousticNode
from core.state import SystemState

log = logging.getLogger("sim.engine")

SCENARIO_DIR = Path(__file__).parent / "scenarios"


class ScenarioEngine:
    def __init__(
        self,
        acoustic_adapter: AcousticAdapter,
        acoustic_node: AcousticNode,
        state: SystemState,
    ) -> None:
        self.acoustic_adapter = acoustic_adapter
        self.acoustic_node = acoustic_node
        self.state = state
        self._task: asyncio.Task | None = None
        self._scenarios: dict[str, dict] = self._load_scenarios()
        # Vision plan + cursor for the active scenario (consumed by Phase 2).
        self.active_vision_plan: dict | None = None
        self._vision_cursor = 0
        self.active_track_plan: dict | None = None

    @staticmethod
    def _load_scenarios() -> dict[str, dict]:
        scenarios: dict[str, dict] = {}
        if not SCENARIO_DIR.exists():
            return scenarios
        for path in sorted(SCENARIO_DIR.glob("*.json")):
            data = json.loads(path.read_text())
            scenarios[data["id"]] = data
        return scenarios

    def list_scenarios(self) -> list[dict]:
        return [
            {"id": s["id"], "name": s.get("name", s["id"]),
             "description": s.get("description", "")}
            for s in self._scenarios.values()
        ]

    def next_vision_response(self) -> dict | None:
        """Return the scripted vision response for the next VisionRequest."""
        plan = self.active_vision_plan
        if not plan:
            return None
        seq = plan.get("sequence", [])
        if self._vision_cursor < len(seq):
            resp = seq[self._vision_cursor]
            self._vision_cursor += 1
            return resp
        return plan.get("default")

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, scenario_id: str) -> bool:
        if scenario_id not in self._scenarios:
            return False
        if self.is_running():
            await self.stop()
        scenario = self._scenarios[scenario_id]
        self.active_vision_plan = scenario.get("vision")
        self.active_track_plan = scenario.get("track")
        self._vision_cursor = 0
        self.state.scenario_active = True
        self.state.scenario_id = scenario_id
        self._task = asyncio.create_task(self._run(scenario))
        return True

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self.state.scenario_active = False

    async def _run(self, scenario: dict) -> None:
        log.info("Scenario '%s' starting", scenario["id"])
        loop = asyncio.get_event_loop()
        t0 = loop.time()
        try:
            for frame in scenario.get("acoustic", []):
                target = t0 + float(frame.get("t", 0.0))
                delay = target - loop.time()
                if delay > 0:
                    await asyncio.sleep(delay)
                profile = AcousticProfile(
                    label=frame.get("label", "ambient"),
                    intensity=float(frame.get("intensity", 0.1)),
                    drone_like=bool(frame.get("drone_like", False)),
                )
                event = self.acoustic_adapter.generate(profile)
                log.info(
                    "acoustic frame t=%.1f class=%s conf=%.2f",
                    frame.get("t", 0.0),
                    event.classification,
                    event.confidence,
                )
                await self.acoustic_node.handle(event)
            log.info("Scenario '%s' acoustic timeline complete", scenario["id"])
        except asyncio.CancelledError:
            log.info("Scenario '%s' cancelled", scenario["id"])
            raise
        finally:
            self.state.scenario_active = False
