"""Escalation / Human-in-the-Loop manager.

Handles operator actions and keeps an audit log. The human is always in control:
no action here ever auto-fires a countermeasure — confirm/escalate only update
the recorded posture and recommendation; stand_down clears the threat. Every
action is appended to an immutable-style audit log for after-action review.
"""

from __future__ import annotations

import logging

from core.event_bus import EventBus
from core.fusion import FusionEngine, recommend
from core.state import SystemState
from core.tracker import Tracker
from models import OperatorAction, now_iso

log = logging.getLogger("core.escalation")


class EscalationManager:
    def __init__(self, bus: EventBus, state: SystemState, fusion: FusionEngine,
                 tracker: Tracker | None = None) -> None:
        self.bus = bus
        self.state = state
        self.fusion = fusion
        self.tracker = tracker
        self.audit_log: list[dict] = []

    def _audit(self, action: OperatorAction, result: str) -> None:
        entry = {
            "ts": now_iso(),
            "action": action.action,
            "assessment_id": action.assessment_id,
            "operator_id": action.operator_id,
            "result": result,
        }
        self.audit_log.append(entry)
        log.info("AUDIT %s", entry)

    async def handle(self, action: OperatorAction) -> dict:
        assessment = self.state.latest_assessment

        if action.action == "stand_down":
            self.fusion.reset()
            if self.tracker is not None:
                self.tracker.reset()
            self.state.reset()
            self._audit(action, "threat_cleared")
            await self.bus.publish("state_snapshot", self.state.snapshot().model_dump())
            return {"result": "stood_down"}

        if action.action == "acknowledge":
            self._audit(action, "acknowledged")
            return {"result": "acknowledged"}

        if action.action == "confirm":
            self._audit(action, "confirmed_by_operator")
            if assessment is not None:
                assessment.recommendation.requires_confirmation = False
                assessment.recommendation.message += " [CONFIRMED by operator]"
                await self.bus.publish("fused_assessment", assessment.model_dump())
                await self.bus.publish("state_snapshot", self.state.snapshot().model_dump())
            return {"result": "confirmed"}

        if action.action == "escalate":
            self._audit(action, "escalated")
            if assessment is not None:
                new_level = min(4, assessment.recommendation.level + 1)
                level_to_threat = {1: "low", 2: "medium", 3: "high", 4: "critical"}
                threat = level_to_threat[new_level]
                bearing = assessment.tracking.bearing_deg if assessment.tracking else 0.0
                assessment.recommendation = recommend(threat, bearing, assessment.source_mode)
                assessment.threat_level = threat  # type: ignore[assignment]
                self.state.threat_level = threat
                await self.bus.publish("fused_assessment", assessment.model_dump())
                await self.bus.publish("state_snapshot", self.state.snapshot().model_dump())
            return {"result": "escalated"}

        self._audit(action, "ignored_unknown")
        return {"result": "ignored"}
