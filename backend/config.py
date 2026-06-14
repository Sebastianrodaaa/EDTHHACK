"""Central configuration and adapter selection.

Single place to swap simulated components for real hardware via env vars —
no other code changes required (the Adapter/Port pattern).
"""

from __future__ import annotations

import os


# Adapter selection (the hardware seam) ------------------------------------- #
ACOUSTIC_ADAPTER = os.getenv("ACOUSTIC_ADAPTER", "simulated")  # simulated | rpi
VISION_ADAPTER = os.getenv("VISION_ADAPTER", "simulated")  # simulated | hosted_cv

# Vision mock behaviour ----------------------------------------------------- #
CV_MOCK_MODE = os.getenv("CV_MOCK_MODE", "scripted")  # scripted | random
VISION_LATENCY_S = float(os.getenv("VISION_LATENCY_S", "0.8"))
VISION_TIMEOUT_S = float(os.getenv("VISION_TIMEOUT_S", "3.0"))

# Acoustic detection thresholds --------------------------------------------- #
ACOUSTIC_CONF_THRESHOLD = float(os.getenv("ACOUSTIC_CONF_THRESHOLD", "0.55"))
# Number of consecutive drone-like frames required before triggering vision
# (temporal gating — suppresses single-frame false positives).
ACOUSTIC_GATE_FRAMES = int(os.getenv("ACOUSTIC_GATE_FRAMES", "2"))
# Cooldown (s) after a trigger before another vision request may fire.
ACOUSTIC_TRIGGER_COOLDOWN_S = float(os.getenv("ACOUSTIC_TRIGGER_COOLDOWN_S", "6.0"))

# Fusion weights ------------------------------------------------------------ #
FUSION_WEIGHT_ACOUSTIC = float(os.getenv("FUSION_WEIGHT_ACOUSTIC", "0.35"))
FUSION_WEIGHT_VISION = float(os.getenv("FUSION_WEIGHT_VISION", "0.65"))
# Acoustic-only assessments are capped below this so vision is always needed
# to reach the highest threat bands.
ACOUSTIC_ONLY_CONF_CAP = float(os.getenv("ACOUSTIC_ONLY_CONF_CAP", "0.55"))

# Gateway ------------------------------------------------------------------- #
EVENT_BUFFER_SIZE = int(os.getenv("EVENT_BUFFER_SIZE", "20"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# External services (future) ------------------------------------------------ #
CV_API_KEY = os.getenv("CV_API_KEY", "")
CV_API_URL = os.getenv("CV_API_URL", "")
RPI_HOST = os.getenv("RPI_HOST", "")

# Live CV escalation / counter-UAS resource staging ------------------------- #
LIVE_CV_INGEST_KEY = os.getenv("LIVE_CV_INGEST_KEY", "")
LIVE_CV_ESCALATION_CONF = float(os.getenv("LIVE_CV_ESCALATION_CONF", "0.70"))
LIVE_CV_DEFAULT_RANGE_M = float(os.getenv("LIVE_CV_DEFAULT_RANGE_M", "260.0"))
SOLDIER_LOCATION = os.getenv("SOLDIER_LOCATION", "Soldier grid BR-042")
COUNTER_UAS_EFFECTOR = os.getenv(
    "COUNTER_UAS_EFFECTOR", "C-UAS response team"
)
COUNTER_UAS_RESOURCES: tuple[str, ...] = tuple(
    item.strip()
    for item in os.getenv(
        "COUNTER_UAS_RESOURCES",
        "RF scanner,jammer kit,spotter team",
    ).split(",")
    if item.strip()
)
COUNTER_UAS_ETA_S = int(os.getenv("COUNTER_UAS_ETA_S", "45"))
