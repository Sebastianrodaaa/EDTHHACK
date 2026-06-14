"""Pydantic event models — the wire contract between backend and mobile C2.

All events are JSON with a `type` discriminant. The schema is locked here in
Phase 1 so every downstream component (vision, fusion, gateway, mobile) shares
one source of truth. See .planning/research/ARCHITECTURE.md for the design.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


def now_iso() -> str:
    """Current UTC time as an ISO-8601 string (the wire format for `ts`)."""
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# --------------------------------------------------------------------------- #
# Acoustic
# --------------------------------------------------------------------------- #

AcousticClass = Literal["drone_like", "noise", "unknown"]


class AcousticFeatures(BaseModel):
    rms: float = Field(ge=0.0, le=1.0)
    snr_db: float
    dominant_freq_hz: float
    band_low: float = Field(ge=0.0, le=1.0)
    band_mid: float = Field(ge=0.0, le=1.0)
    band_high: float = Field(ge=0.0, le=1.0)


class AcousticEvent(BaseModel):
    type: Literal["acoustic_event"] = "acoustic_event"
    id: str = Field(default_factory=new_id)
    ts: str = Field(default_factory=now_iso)
    adapter: str = "simulated"
    features: AcousticFeatures
    classification: AcousticClass
    confidence: float = Field(ge=0.0, le=1.0)


# --------------------------------------------------------------------------- #
# Vision
# --------------------------------------------------------------------------- #

VisionClass = Literal["drone", "bird", "aircraft", "unknown"]


class BoundingBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class VisionRequest(BaseModel):
    """Internal only — Acoustic Node → Vision Worker."""

    type: Literal["vision_request"] = "vision_request"
    id: str = Field(default_factory=new_id)
    ts: str = Field(default_factory=now_iso)
    trigger_acoustic_id: str
    acoustic_confidence: float = Field(ge=0.0, le=1.0)


class VisionEvent(BaseModel):
    type: Literal["vision_event"] = "vision_event"
    id: str = Field(default_factory=new_id)
    ts: str = Field(default_factory=now_iso)
    trigger_acoustic_id: str
    adapter: str = "simulated"
    classification: VisionClass
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: Optional[BoundingBox] = None


class VisionTimeout(BaseModel):
    type: Literal["vision_timeout"] = "vision_timeout"
    id: str = Field(default_factory=new_id)
    ts: str = Field(default_factory=now_iso)
    trigger_acoustic_id: str
    timeout_s: float


# --------------------------------------------------------------------------- #
# Fusion / threat / recommendation
# --------------------------------------------------------------------------- #

ThreatLevel = Literal["low", "medium", "high", "critical"]

# 1=monitor, 2=request_visual, 3=alert_squad, 4=prepare_countermeasures
RecAction = Literal[
    "monitor", "request_visual", "alert_squad", "prepare_countermeasures"
]


class Recommendation(BaseModel):
    level: int = Field(ge=1, le=4)
    action: RecAction
    message: str
    requires_confirmation: bool = True


class Tracking(BaseModel):
    track_id: Optional[str] = None
    state: Literal["acquiring", "tracking", "lost", "terminated"] = "acquiring"
    bearing_deg: float = 0.0
    range_m: Optional[float] = None
    speed_mps: Optional[float] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    last_updated: str = Field(default_factory=now_iso)


class FusedAssessment(BaseModel):
    type: Literal["fused_assessment"] = "fused_assessment"
    id: str = Field(default_factory=new_id)
    ts: str = Field(default_factory=now_iso)
    threat_level: ThreatLevel
    confidence: float = Field(ge=0.0, le=1.0)
    acoustic_confidence: float = Field(ge=0.0, le=1.0)
    vision_confidence: Optional[float] = None
    source_mode: Literal["fused", "acoustic_only"] = "fused"
    recommendation: Recommendation
    tracking: Optional[Tracking] = None


# --------------------------------------------------------------------------- #
# Tracking stream (Phase 5)
# --------------------------------------------------------------------------- #


class TrackUpdate(BaseModel):
    type: Literal["track_update"] = "track_update"
    id: str = Field(default_factory=new_id)
    ts: str = Field(default_factory=now_iso)
    track_id: str
    state: Literal["acquiring", "tracking", "lost", "terminated"]
    bearing_deg: float
    range_m: float
    speed_mps: float
    confidence: float = Field(ge=0.0, le=1.0)


# --------------------------------------------------------------------------- #
# Operator action (Mobile C2 → Gateway)
# --------------------------------------------------------------------------- #

OperatorActionType = Literal["acknowledge", "confirm", "stand_down", "escalate"]


class OperatorAction(BaseModel):
    type: Literal["operator_action"] = "operator_action"
    ts: str = Field(default_factory=now_iso)
    action: OperatorActionType
    assessment_id: Optional[str] = None
    operator_id: str = "op-1"


# --------------------------------------------------------------------------- #
# Reasoning trail (matches the mobile app's Task[] / Subtask[] shape)
# --------------------------------------------------------------------------- #

StepStatus = Literal["completed", "in-progress", "pending", "need-help", "failed"]


class ReasoningSubtask(BaseModel):
    id: str
    title: str
    description: str = ""
    status: StepStatus = "pending"
    tools: list[str] = Field(default_factory=list)


class ReasoningTask(BaseModel):
    id: str
    title: str
    description: str = ""
    status: StepStatus = "pending"
    level: int = 0
    dependencies: list[str] = Field(default_factory=list)
    subtasks: list[ReasoningSubtask] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# State snapshot (Gateway → Mobile C2 on connect / GET /state)
# --------------------------------------------------------------------------- #


class StateSnapshot(BaseModel):
    type: Literal["state_snapshot"] = "state_snapshot"
    ts: str = Field(default_factory=now_iso)
    orb_mode: Literal["white", "red"] = "white"
    threat_level: ThreatLevel = "low"
    latest_assessment: Optional[FusedAssessment] = None
    reasoning_steps: list[ReasoningTask] = Field(default_factory=list)
    subsystems: dict[str, str] = Field(default_factory=dict)
    tracking: Optional[Tracking] = None
    scenario_active: bool = False
    scenario_id: Optional[str] = None


class StateSync(BaseModel):
    """Replayed buffer of recent events sent to a (re)connecting client."""

    type: Literal["state_sync"] = "state_sync"
    ts: str = Field(default_factory=now_iso)
    events: list[dict] = Field(default_factory=list)
