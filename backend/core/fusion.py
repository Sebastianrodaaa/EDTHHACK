"""Fusion Engine — late fusion, threat scoring, recommendation, reasoning trail.

Subscribes to the pipeline event types and advances the operator-facing state:
  - acoustic_event (drone-like)  → early-warning: orb red, reasoning ACOUSTIC_HOT
  - vision_request               → reasoning VISION_PENDING (analysing POV)
  - vision_event                 → weighted late fusion → FusedAssessment
  - vision_timeout               → acoustic-only assessment (capped confidence)

Fusion is a weighted sum (vision is the confirmation modality, so it carries
more weight). Threat bands map to a 4-level escalation recommendation. The
recommendation always requires human confirmation for actionable levels.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import config
from core import reasoning
from core.event_bus import EventBus
from core.reasoning import Stage
from core.state import SystemState
from models import (
    AcousticEvent,
    CounterUASDispatch,
    FusedAssessment,
    Recommendation,
    Tracking,
    VisionDetectionIn,
    VisionEvent,
    VisionTimeout,
    now_iso,
)

log = logging.getLogger("core.fusion")

TrackPlanProvider = Callable[[], Optional[dict]]


def threat_band(fused: float) -> str:
    if fused >= 0.85:
        return "critical"
    if fused >= 0.70:
        return "high"
    if fused >= 0.50:
        return "medium"
    return "low"


def recommend(threat_level: str, bearing_deg: float, source_mode: str) -> Recommendation:
    bearing = f"{bearing_deg:.0f}°"
    if threat_level == "critical":
        return Recommendation(
            level=4, action="prepare_countermeasures",
            message=f"Drone confirmed inbound at {bearing}. Prepare countermeasure options — operator authorization required.",
            requires_confirmation=True)
    if threat_level == "high":
        return Recommendation(
            level=3, action="alert_squad",
            message=f"Drone-like signature confirmed visually at {bearing}. Alert squad.",
            requires_confirmation=True)
    if threat_level == "medium":
        if source_mode == "acoustic_only":
            return Recommendation(
                level=2, action="request_visual",
                message=f"Drone-like sound at {bearing}, no visual yet. Request secondary visual confirmation.",
                requires_confirmation=True)
        return Recommendation(
            level=2, action="request_visual",
            message=f"Possible drone at {bearing}. Request secondary confirmation before escalating.",
            requires_confirmation=True)
    return Recommendation(
        level=1, action="monitor",
        message="Low-confidence contact. Continue monitoring.",
        requires_confirmation=False)


def recommend_dispatch(bearing_deg: float, dispatch: CounterUASDispatch) -> Recommendation:
    bearing = f"{bearing_deg:.0f}°"
    resources = ", ".join(dispatch.resources) if dispatch.resources else dispatch.effector
    return Recommendation(
        level=5,
        action="dispatch_counter_uas",
        message=(
            f"Drone confirmed by live POV at {bearing}. Dispatch {dispatch.effector} "
            f"to {dispatch.soldier_location}; resources: {resources}; "
            f"ETA {dispatch.eta_s}s. Operator authorization required before effects."
        ),
        requires_confirmation=True,
    )


class FusionEngine:
    def __init__(self, bus: EventBus, state: SystemState,
                 track_plan_provider: Optional[TrackPlanProvider] = None) -> None:
        self.bus = bus
        self.state = state
        self._track_plan_provider = track_plan_provider
        self._stage = Stage.LISTENING
        self._acoustic_conf: dict[str, float] = {}
        self._tasks: list = []
        self._dispatch_active = False

    # -- lifecycle -------------------------------------------------------- #
    def start(self) -> None:
        import asyncio
        self._tasks = [
            asyncio.create_task(self._consume("acoustic_event", self._on_acoustic)),
            asyncio.create_task(self._consume("vision_request", self._on_vision_request)),
            asyncio.create_task(self._consume("vision_event", self._on_vision_event)),
            asyncio.create_task(self._consume("vision_timeout", self._on_vision_timeout)),
        ]

    async def stop(self) -> None:
        import asyncio
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._tasks = []

    def reset(self) -> None:
        self._stage = Stage.LISTENING
        self._acoustic_conf.clear()
        self._dispatch_active = False

    async def _consume(self, event_type: str, handler) -> None:
        async for payload in self.bus.stream(event_type):
            try:
                await handler(payload)
            except Exception as exc:  # noqa: BLE001
                log.warning("fusion handler error on %s: %s", event_type, exc)

    # -- bearing ---------------------------------------------------------- #
    def _bearing(self) -> float:
        if self.state.tracking is not None:
            return self.state.tracking.bearing_deg
        plan = self._track_plan_provider() if self._track_plan_provider else None
        if plan:
            return float(plan.get("initial_bearing_deg", 0.0))
        return 0.0

    async def _advance(self, stage: Stage, **ctx) -> None:
        self._stage = stage
        self.state.reasoning_steps = reasoning.for_stage(stage, **ctx)
        await self._broadcast_state()

    async def _broadcast_state(self) -> None:
        await self.bus.publish("state_snapshot", self.state.snapshot().model_dump())

    # -- handlers --------------------------------------------------------- #
    async def _on_acoustic(self, payload: dict) -> None:
        event = AcousticEvent(**payload)
        is_hot = (
            event.classification == "drone_like"
            and event.confidence >= config.ACOUSTIC_CONF_THRESHOLD
        )
        if is_hot and self._stage < Stage.ACOUSTIC_HOT:
            # Early warning: orb red the moment a credible signature appears.
            self.state.orb_mode = "red"
            self.state.threat_level = "medium"
            await self._advance(Stage.ACOUSTIC_HOT)
            log.info("ACOUSTIC_HOT — early warning, orb red")

    async def _on_vision_request(self, payload: dict) -> None:
        self._acoustic_conf[payload["trigger_acoustic_id"]] = payload["acoustic_confidence"]
        if self._stage < Stage.VISION_PENDING:
            self.state.subsystems["vision"] = "active"
            await self._advance(Stage.VISION_PENDING)
            log.info("VISION_PENDING — analysing POV feed")

    async def _on_vision_event(self, payload: dict) -> None:
        if self._stage >= Stage.DISPATCH:
            log.info("ignoring scripted vision_event after live-CV dispatch")
            return
        event = VisionEvent(**payload)
        acoustic_conf = self._acoustic_conf.get(event.trigger_acoustic_id, 0.6)

        await self._advance(Stage.VISION_CONFIRMED, vision_class=event.classification)

        # A non-drone visual (bird/aircraft) downweights the vision contribution.
        vision_conf = event.confidence
        if event.classification != "drone":
            vision_conf = max(0.0, vision_conf * 0.3)

        fused = (
            acoustic_conf * config.FUSION_WEIGHT_ACOUSTIC
            + vision_conf * config.FUSION_WEIGHT_VISION
        )
        level = threat_band(fused)
        bearing = self._bearing()

        tracking = Tracking(
            state="acquiring", bearing_deg=bearing,
            confidence=round(fused, 3), last_updated=now_iso())

        assessment = FusedAssessment(
            threat_level=level,  # type: ignore[arg-type]
            confidence=round(fused, 3),
            acoustic_confidence=round(acoustic_conf, 3),
            vision_confidence=round(event.confidence, 3),
            source_mode="fused",
            recommendation=recommend(level, bearing, "fused"),
            tracking=tracking,
        )
        await self._emit_assessment(assessment, vision_class=event.classification)

    async def _on_vision_timeout(self, payload: dict) -> None:
        if self._stage >= Stage.DISPATCH:
            log.info("ignoring vision_timeout after live-CV dispatch")
            return
        timeout = VisionTimeout(**payload)
        acoustic_conf = self._acoustic_conf.get(timeout.trigger_acoustic_id, 0.6)
        # Acoustic-only: cap confidence so vision is always needed for top bands.
        fused = min(acoustic_conf, config.ACOUSTIC_ONLY_CONF_CAP)
        level = threat_band(fused)
        bearing = self._bearing()

        self.state.subsystems["vision"] = "degraded"
        self._stage = Stage.TIMEOUT
        self.state.reasoning_steps = reasoning.for_stage(Stage.TIMEOUT)

        assessment = FusedAssessment(
            threat_level=level,  # type: ignore[arg-type]
            confidence=round(fused, 3),
            acoustic_confidence=round(acoustic_conf, 3),
            vision_confidence=None,
            source_mode="acoustic_only",
            recommendation=recommend(level, bearing, "acoustic_only"),
            tracking=Tracking(state="acquiring", bearing_deg=bearing,
                              confidence=round(fused, 3)),
        )
        log.info("acoustic-only assessment (vision timeout): level=%s conf=%.2f",
                 level, fused)
        await self.bus.publish("fused_assessment", assessment.model_dump())
        self.state.latest_assessment = assessment
        self.state.threat_level = level
        await self._broadcast_state()

    async def _emit_assessment(self, assessment: FusedAssessment, vision_class: str) -> None:
        self.state.latest_assessment = assessment
        self.state.threat_level = assessment.threat_level
        self.state.tracking = assessment.tracking
        self.state.orb_mode = "red" if assessment.threat_level != "low" else "white"
        self.state.subsystems["fusion"] = "online"
        self.state.subsystems["tracking"] = "active"

        log.info(
            "FUSED assessment: level=%s conf=%.2f (acoustic=%.2f vision=%.2f) rec=%s",
            assessment.threat_level, assessment.confidence,
            assessment.acoustic_confidence, assessment.vision_confidence or 0.0,
            assessment.recommendation.action,
        )
        await self.bus.publish("fused_assessment", assessment.model_dump())
        await self._advance(
            Stage.ASSESSED,
            bearing_deg=assessment.tracking.bearing_deg if assessment.tracking else None,
            fused_conf=assessment.confidence,
            vision_class=vision_class,
        )

    async def inject_real_vision(self, detection: VisionDetectionIn) -> dict:
        """Escalate the live overlay's drone detection into the C2 pipeline."""
        self.state.subsystems["vision"] = "online"

        if self._dispatch_active:
            return {
                "escalated": False,
                "reason": "already_dispatched",
                "assessment_id": (
                    self.state.latest_assessment.id
                    if self.state.latest_assessment is not None
                    else None
                ),
            }

        if (
            detection.classification != "drone"
            or detection.confidence < config.LIVE_CV_ESCALATION_CONF
        ):
            await self._advance(
                Stage.VISION_CONFIRMED,
                vision_class=detection.classification,
            )
            log.info(
                "live vision ignored for dispatch: class=%s conf=%.2f",
                detection.classification,
                detection.confidence,
            )
            return {
                "escalated": False,
                "reason": "not_drone_or_low_confidence",
                "classification": detection.classification,
                "confidence": detection.confidence,
            }

        # Set synchronously before any await so concurrent posts cannot double-dispatch.
        self._dispatch_active = True
        self._stage = Stage.DISPATCH

        bearing = (
            detection.bearing_deg
            if detection.bearing_deg is not None
            else self._bearing()
        )
        fused = min(0.99, detection.confidence)

        tracking = Tracking(
            state="acquiring",
            bearing_deg=round(float(bearing), 1),
            range_m=config.LIVE_CV_DEFAULT_RANGE_M,
            speed_mps=12.0,
            confidence=round(fused, 3),
            last_updated=now_iso(),
        )
        dispatch = CounterUASDispatch(
            effector=config.COUNTER_UAS_EFFECTOR,
            resources=list(config.COUNTER_UAS_RESOURCES),
            eta_s=config.COUNTER_UAS_ETA_S,
            target_bearing_deg=tracking.bearing_deg,
            soldier_location=config.SOLDIER_LOCATION,
        )
        assessment = FusedAssessment(
            threat_level="critical",
            confidence=round(fused, 3),
            acoustic_confidence=0.0,
            vision_confidence=round(detection.confidence, 3),
            source_mode="vision_only",
            recommendation=recommend_dispatch(tracking.bearing_deg, dispatch),
            tracking=tracking,
            dispatch=dispatch,
        )

        self.state.latest_assessment = assessment
        self.state.threat_level = "critical"
        self.state.tracking = tracking
        self.state.orb_mode = "red"
        self.state.subsystems["fusion"] = "online"
        self.state.subsystems["tracking"] = "active"

        log.info(
            "LIVE CV dispatch: class=%s conf=%.2f bearing=%.1f eta=%ss",
            detection.classification,
            detection.confidence,
            tracking.bearing_deg,
            dispatch.eta_s,
        )
        await self.bus.publish("fused_assessment", assessment.model_dump())
        await self._advance(
            Stage.DISPATCH,
            bearing_deg=tracking.bearing_deg,
            fused_conf=assessment.confidence,
            vision_class=detection.classification,
            dispatch_effector=dispatch.effector,
            soldier_location=dispatch.soldier_location,
        )
        return {
            "escalated": True,
            "assessment_id": assessment.id,
            "threat_level": assessment.threat_level,
            "recommendation": assessment.recommendation.action,
            "dispatch": dispatch.model_dump(),
        }
