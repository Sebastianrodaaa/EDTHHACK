"""In-memory system state — the snapshot served to (re)connecting clients."""

from __future__ import annotations

from models import (
    FusedAssessment,
    ReasoningTask,
    StateSnapshot,
    Tracking,
)


class SystemState:
    def __init__(self) -> None:
        self.orb_mode: str = "white"
        self.threat_level: str = "low"
        self.latest_assessment: FusedAssessment | None = None
        self.reasoning_steps: list[ReasoningTask] = []
        self.tracking: Tracking | None = None
        self.scenario_active: bool = False
        self.scenario_id: str | None = None
        self.subsystems: dict[str, str] = {
            "acoustic": "online",
            "vision": "standby",
            "fusion": "online",
            "tracking": "standby",
        }

    def snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            orb_mode=self.orb_mode,  # type: ignore[arg-type]
            threat_level=self.threat_level,  # type: ignore[arg-type]
            latest_assessment=self.latest_assessment,
            reasoning_steps=self.reasoning_steps,
            subsystems=self.subsystems,
            tracking=self.tracking,
            scenario_active=self.scenario_active,
            scenario_id=self.scenario_id,
        )

    def reset(self) -> None:
        self.orb_mode = "white"
        self.threat_level = "low"
        self.latest_assessment = None
        self.reasoning_steps = []
        self.tracking = None
        self.subsystems["vision"] = "standby"
        self.subsystems["tracking"] = "standby"
