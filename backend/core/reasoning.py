"""Server-side reasoning cascade — mirrors the mobile app's Task[] shape exactly.

The mobile ReasoningTrail renders `Task`/`Subtask` objects (see src/store.ts).
The backend drives that trail live by advancing these same tasks through pipeline
stages, so the app needs no structural changes — it just renders server state.
"""

from __future__ import annotations

from enum import IntEnum

from models import ReasoningSubtask, ReasoningTask


class Stage(IntEnum):
    LISTENING = 0
    ACOUSTIC_HOT = 1
    VISION_PENDING = 2
    VISION_CONFIRMED = 3
    ASSESSED = 4
    TIMEOUT = 5


def build_tasks() -> list[ReasoningTask]:
    """Base cascade — identical ids/titles to the mobile app's buildTasks()."""
    return [
        ReasoningTask(
            id="1", title="Acoustic Signal Acquisition", level=0,
            description="Ingest and condition the body-worn mic-array stream.",
            status="in-progress", dependencies=[],
            subtasks=[
                ReasoningSubtask(id="1.1", title="Capture audio frame",
                    description="Buffer 50 ms frames from the mic array.",
                    status="in-progress", tools=["mic-array", "audio-buffer"]),
                ReasoningSubtask(id="1.2", title="Compute RMS & SNR",
                    description="Measure level against the ambient noise floor.",
                    status="pending", tools=["dsp-engine"]),
                ReasoningSubtask(id="1.3", title="Detect energy spike",
                    description="Flag frames crossing the adaptive threshold.",
                    status="pending", tools=["vad", "dsp-engine"]),
            ],
        ),
        ReasoningTask(
            id="2", title="Spectral Analysis", level=0,
            description="Extract frequency-domain features from the frame.",
            status="pending", dependencies=[],
            subtasks=[
                ReasoningSubtask(id="2.1", title="FFT / spectrogram",
                    description="Transform the frame into the frequency domain.",
                    status="pending", tools=["dsp-engine"]),
                ReasoningSubtask(id="2.2", title="Dominant frequency",
                    description="Locate the fundamental rotor / prop tone.",
                    status="pending", tools=["peak-finder"]),
                ReasoningSubtask(id="2.3", title="Harmonic comb check",
                    description="Detect evenly spaced harmonics of the fundamental.",
                    status="pending", tools=["harmonic-analyzer"]),
            ],
        ),
        ReasoningTask(
            id="3", title="Classification", level=1,
            description="Decide whether the signature is drone-like.",
            status="pending", dependencies=["1", "2"],
            subtasks=[
                ReasoningSubtask(id="3.1", title="Match signature library",
                    description="Compare features against known UAS profiles.",
                    status="pending", tools=["signature-db"]),
                ReasoningSubtask(id="3.2", title="Confirm with POV vision",
                    description="Pull the POV frame and run object detection.",
                    status="pending", tools=["pov-camera", "cv-model"]),
                ReasoningSubtask(id="3.3", title="Calibrate confidence",
                    description="Temperature-scale the raw classifier score.",
                    status="pending", tools=["calibrator"]),
            ],
        ),
        ReasoningTask(
            id="4", title="Threat Assessment", level=1,
            description="Localize the source and recommend operator action.",
            status="pending", dependencies=["3"],
            subtasks=[
                ReasoningSubtask(id="4.1", title="Estimate bearing",
                    description="Direction-of-arrival from inter-mic phase delay.",
                    status="pending", tools=["doa-estimator"]),
                ReasoningSubtask(id="4.2", title="Fuse sound + vision",
                    description="Weighted late fusion of both confidences.",
                    status="pending", tools=["fusion-engine"]),
                ReasoningSubtask(id="4.3", title="Recommend action",
                    description="Advise the operator; await confirmation.",
                    status="pending", tools=["c2-advisor"]),
            ],
        ),
    ]


def _set(tasks: list[ReasoningTask], task_id: str, status: str,
         sub_id: str | None = None, description: str | None = None) -> None:
    for t in tasks:
        if t.id != task_id:
            continue
        if sub_id is None:
            t.status = status  # type: ignore[assignment]
            if description:
                t.description = description
            return
        for s in t.subtasks:
            if s.id == sub_id:
                s.status = status  # type: ignore[assignment]
                if description:
                    s.description = description
                return


def for_stage(stage: Stage, *, bearing_deg: float | None = None,
              fused_conf: float | None = None,
              vision_class: str | None = None) -> list[ReasoningTask]:
    """Build the full task list with statuses reflecting the given stage."""
    tasks = build_tasks()

    if stage >= Stage.ACOUSTIC_HOT:
        for sub in ("1.1", "1.2", "1.3"):
            _set(tasks, "1", "completed", sub)
        _set(tasks, "1", "completed")
        _set(tasks, "2", "in-progress")
        _set(tasks, "2", "in-progress", "2.1")

    if stage >= Stage.VISION_PENDING:
        for sub in ("2.1", "2.2", "2.3"):
            _set(tasks, "2", "completed", sub)
        _set(tasks, "2", "completed")
        _set(tasks, "3", "in-progress")
        _set(tasks, "3", "completed", "3.1")
        _set(tasks, "3", "in-progress", "3.2",
             description="Pulling POV frame, running object detection…")

    if stage >= Stage.VISION_CONFIRMED:
        label = vision_class or "drone"
        _set(tasks, "3", "completed", "3.2",
             description=f"POV vision confirmed: {label}.")
        _set(tasks, "3", "in-progress", "3.3")

    if stage >= Stage.ASSESSED:
        _set(tasks, "3", "completed", "3.3")
        _set(tasks, "3", "completed")
        _set(tasks, "4", "in-progress")
        if bearing_deg is not None:
            _set(tasks, "4", "completed", "4.1",
                 description=f"Bearing {bearing_deg:.0f}° from operator.")
        else:
            _set(tasks, "4", "completed", "4.1")
        if fused_conf is not None:
            _set(tasks, "4", "completed", "4.2",
                 description=f"Fused confidence {fused_conf:.0%}.")
        else:
            _set(tasks, "4", "completed", "4.2")
        _set(tasks, "4", "need-help", "4.3",
             description="Recommendation issued — awaiting operator decision.")
        _set(tasks, "4", "need-help")

    if stage == Stage.TIMEOUT:
        # Vision unavailable — acoustic-only path, ask operator for a visual.
        for sub in ("2.1", "2.2", "2.3"):
            _set(tasks, "2", "completed", sub)
        _set(tasks, "2", "completed")
        _set(tasks, "3", "completed", "3.1")
        _set(tasks, "3", "failed", "3.2",
             description="POV vision timed out — no visual confirmation.")
        _set(tasks, "3", "need-help")
        _set(tasks, "4", "need-help")
        _set(tasks, "4", "need-help", "4.3",
             description="Acoustic-only — request manual visual confirmation.")

    return tasks
