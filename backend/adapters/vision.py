"""Vision adapter — the seam for the POV camera + CV model.

`SimulatedVisionAdapter` returns a classification for each VisionRequest. In
`scripted` mock mode it pulls the next response from the active scenario's
vision plan (deterministic demo); in `random` mode it fabricates a plausible
result. A future `HostedCVModelAdapter` would POST the live POV frame to a
hosted object-detection API and map the response onto the same `VisionEvent`.
"""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Optional

import config
from models import BoundingBox, VisionEvent, VisionRequest


class VisionAdapter(ABC):
    @abstractmethod
    async def analyze(self, request: VisionRequest) -> VisionEvent:
        """Analyse the POV feed for the requested detection window."""


ResponseProvider = Callable[[], Optional[dict]]


class SimulatedVisionAdapter(VisionAdapter):
    def __init__(self, response_provider: Optional[ResponseProvider] = None) -> None:
        self._provider = response_provider

    async def analyze(self, request: VisionRequest) -> VisionEvent:
        # Simulate model inference latency on the event loop (never blocks it).
        await asyncio.sleep(config.VISION_LATENCY_S)

        scripted = self._provider() if (
            config.CV_MOCK_MODE == "scripted" and self._provider
        ) else None

        if scripted is not None:
            bbox = scripted.get("bounding_box")
            return VisionEvent(
                trigger_acoustic_id=request.trigger_acoustic_id,
                adapter="simulated",
                classification=scripted.get("classification", "unknown"),
                confidence=float(scripted.get("confidence", 0.5)),
                bounding_box=BoundingBox(**bbox) if bbox else None,
            )

        # Random mock — bias toward drone since acoustic already flagged hot.
        roll = random.random()
        if roll < 0.7:
            classification, conf = "drone", random.uniform(0.78, 0.95)
            bbox = BoundingBox(
                x=round(random.uniform(0.2, 0.6), 2),
                y=round(random.uniform(0.1, 0.4), 2),
                w=round(random.uniform(0.06, 0.16), 2),
                h=round(random.uniform(0.04, 0.10), 2),
            )
        elif roll < 0.85:
            classification, conf, bbox = "bird", random.uniform(0.4, 0.7), None
        else:
            classification, conf, bbox = "unknown", random.uniform(0.1, 0.4), None

        return VisionEvent(
            trigger_acoustic_id=request.trigger_acoustic_id,
            adapter="simulated",
            classification=classification,  # type: ignore[arg-type]
            confidence=round(conf, 3),
            bounding_box=bbox,
        )


class HostedCVModelAdapter(VisionAdapter):
    """Future: POST live POV JPEG frame to a hosted detector. Stubbed for now."""

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    async def analyze(self, request: VisionRequest) -> VisionEvent:  # pragma: no cover
        raise NotImplementedError(
            "HostedCVModelAdapter requires CV_API_URL/CV_API_KEY and a live frame source."
        )
