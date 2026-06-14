"""Acoustic adapter — the hardware seam for the microphone node.

The simulated adapter synthesises realistic acoustic *features* from a scenario
profile. A future `RpiAcousticAdapter` would compute the same features from real
PCM frames streamed off a Raspberry Pi mic array; the rest of the system only
depends on the `AcousticEvent` it returns, so swapping is a one-line change in
config.py.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

from models import AcousticEvent, AcousticFeatures


@dataclass
class AcousticProfile:
    """A scenario's intent for one acoustic frame, before feature synthesis."""

    label: str = "ambient"  # ambient | drone | wind | speech
    intensity: float = 0.1  # 0 quiet .. 1 loud
    drone_like: bool = False


class AcousticAdapter(ABC):
    @abstractmethod
    def generate(self, profile: AcousticProfile) -> AcousticEvent:
        """Produce one fully-populated AcousticEvent from a frame profile."""


class SimulatedAcousticAdapter(AcousticAdapter):
    """Synthesises acoustic features with light randomness for realism."""

    def generate(self, profile: AcousticProfile) -> AcousticEvent:
        jitter = lambda s=0.04: random.uniform(-s, s)  # noqa: E731
        clamp = lambda v: max(0.0, min(1.0, v))  # noqa: E731

        intensity = clamp(profile.intensity + jitter())

        if profile.drone_like:
            # Drones: strong low-band rotor fundamental + high-band shimmer,
            # narrow tonal peak, decent SNR.
            rms = clamp(0.35 + 0.45 * intensity + jitter())
            band_low = clamp(0.30 + 0.45 * intensity + jitter())
            band_mid = clamp(0.12 + 0.10 * intensity + jitter())
            band_high = clamp(0.30 + 0.40 * intensity + jitter())
            dominant_freq_hz = round(80.0 + 40.0 * intensity + jitter(8.0), 1)
            snr_db = round(8.0 + 10.0 * intensity + jitter(1.5), 1)
            # Confidence rises with intensity + spectral structure.
            confidence = clamp(0.45 + 0.45 * intensity + jitter(0.05))
            classification = "drone_like" if confidence >= 0.5 else "unknown"
        else:
            # Ambient/wind/speech: broadband, low tonal structure, poor SNR.
            rms = clamp(0.05 + 0.35 * intensity + jitter())
            band_low = clamp(0.10 + 0.25 * intensity + jitter())
            band_mid = clamp(0.10 + 0.30 * intensity + jitter())
            band_high = clamp(0.05 + 0.20 * intensity + jitter())
            dominant_freq_hz = round(200.0 + 1500.0 * random.random(), 1)
            snr_db = round(-2.0 + 6.0 * intensity + jitter(1.5), 1)
            confidence = clamp(0.10 + 0.25 * intensity + jitter(0.05))
            classification = "noise"

        return AcousticEvent(
            adapter="simulated",
            features=AcousticFeatures(
                rms=round(rms, 3),
                snr_db=snr_db,
                dominant_freq_hz=dominant_freq_hz,
                band_low=round(band_low, 3),
                band_mid=round(band_mid, 3),
                band_high=round(band_high, 3),
            ),
            classification=classification,
            confidence=round(confidence, 3),
        )
