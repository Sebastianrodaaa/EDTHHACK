# Architecture Research

**Domain:** Body-worn counter-UAS acoustic-vision C2 system (simulated demo)
**Researched:** 2026-06-14
**Confidence:** HIGH — architecture derived from existing codebase, domain requirements in PROJECT.md, and established patterns for sensor-fusion event pipelines

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SIMULATION LAYER                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Scenario Driver  (sim/scenario.py)                                   │   │
│  │  Controls event timing, injects acoustic + vision payloads into       │   │
│  │  adapters. Drives the repeatable end-to-end demo script.              │   │
│  └──────────────┬─────────────────────────────┬────────────────────────┘   │
│                 │ AcousticConfig               │ VisionConfig                │
├─────────────────▼─────────────────────────────▼────────────────────────────┤
│                       SENSOR ADAPTER LAYER  (adapters/)                      │
│  ┌───────────────────────────┐  ┌─────────────────────────────────────────┐ │
│  │  AcousticAdapter (ABC)    │  │  VisionAdapter (ABC)                    │ │
│  │  ├ SimulatedAcoustic      │  │  ├ SimulatedVision                      │ │
│  │  └ RpiAcoustic  [future]  │  │  ├ HostedCVModel  [future]              │ │
│  └────────────┬──────────────┘  │  └ MetaGlasses    [future]              │ │
│               │ AcousticEvent   └────────────────┬────────────────────────┘ │
│               │                                  │ VisionEvent              │
├───────────────▼──────────────────────────────────▼────────────────────────┤
│                       PROCESSING LAYER  (core/)                              │
│  ┌──────────────────┐   ┌──────────────────┐   ┌───────────────────────┐  │
│  │  Acoustic Node   │   │  Vision Worker   │   │  Fusion Engine        │  │
│  │  acoustic_node.py│   │  vision_worker.py│   │  fusion.py            │  │
│  │                  │──▶│                  │──▶│                       │  │
│  │  Consumes        │   │  Receives        │   │  Late fusion:         │  │
│  │  AcousticEvents  │   │  VisionRequest   │   │  acoustic + vision    │  │
│  │  Applies thresh  │   │  Returns         │   │  confidence →         │  │
│  │  Publishes       │   │  VisionEvent     │   │  FusedAssessment      │  │
│  │  VisionRequest   │   │                  │   │  + Recommendation     │  │
│  └──────────────────┘   └──────────────────┘   └──────────┬────────────┘  │
│                                                             │               │
├─────────────────────────────────────────────────────────────▼───────────────┤
│                       GATEWAY LAYER  (gateway/)                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  FastAPI + WebSocket Gateway  (main.py / gateway/ws.py)               │   │
│  │                                                                        │   │
│  │  • WebSocket /ws — event stream to mobile C2 (JSON messages)          │   │
│  │  • REST GET /state — current threat state snapshot                    │   │
│  │  • REST POST /scenario/{id}/start — trigger scenario from C2          │   │
│  │  • REST POST /operator/action — receive operator acknowledgements     │   │
│  │  • Internal pub/sub bus (asyncio Queue or lightweight broker)         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │ WebSocket (JSON)                        │
├────────────────────────────────────▼────────────────────────────────────────┤
│                       MOBILE C2 LAYER  (existing Expo/RN app)                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  WebSocket Client  (src/transport/useServerEvents.ts)                 │   │
│  │  zustand store  (src/store.ts) — receives live server events          │   │
│  │  AcousticOrb  (src/components/AcousticOrb.tsx)                       │   │
│  │  ReasoningTrail  (src/components/ReasoningTrail.tsx)                  │   │
│  │  ThreatPanel  (new) — confidence meter + recommendation cards         │   │
│  │  TrackingMap  (new, simulated) — bearing + trajectory overlay        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Owns | Does NOT Own | Communicates With |
|-----------|------|--------------|-------------------|
| **Scenario Driver** | Scenario scripts, event timing, demo playback | Sensor logic, fusion math | Injects into adapters via constructor/config |
| **AcousticAdapter** | Audio sampling / simulation of acoustic features | Detection thresholds, fusion | Emits `AcousticEvent` → Acoustic Node |
| **VisionAdapter** | Frame capture / CV model call / sim response | Fusion scoring, recommendation | Returns `VisionEvent` to Vision Worker |
| **Acoustic Node** | Detection threshold, feature extraction trigger | Vision pipeline, fusion | → publishes `VisionRequest`; ← consumes `AcousticEvent` |
| **Vision Worker** | Vision request lifecycle, timeout handling | Acoustic pipeline, fusion | → publishes `VisionEvent`; calls VisionAdapter |
| **Fusion Engine** | Late fusion math, threat scoring, recommendation generation | Transport, UI | → publishes `FusedAssessment` to Gateway |
| **FastAPI Gateway** | WebSocket sessions, REST endpoints, internal event routing | Sensor logic, fusion | ↔ Processing layer (asyncio); → Mobile C2 (WS) |
| **Mobile C2** | Operator UI, display state, operator actions | Backend logic | ↔ Gateway (WebSocket); → operator input |

---

## Event Schema

All events are JSON. The `type` field is the discriminant. The server publishes to the WebSocket stream; the client sends `OperatorAction` back.

### `acoustic_event`
```jsonc
{
  "type": "acoustic_event",
  "id": "uuid",
  "ts": "2026-06-14T04:59:00.000Z",   // ISO8601 UTC
  "adapter": "simulated",              // or "rpi"
  "features": {
    "rms": 0.42,                       // root-mean-square energy 0–1
    "snr_db": 12.5,                    // signal-to-noise ratio dB
    "dominant_freq_hz": 87.3,          // fundamental rotor tone
    "band_low": 0.31,                  // energy 20–300 Hz band
    "band_mid": 0.18,                  // energy 300–2k Hz band
    "band_high": 0.44                  // energy 2k–8k Hz band (rotor shimmer)
  },
  "classification": "drone_like",      // "drone_like" | "noise" | "unknown"
  "confidence": 0.78                   // acoustic classifier score 0–1
}
```

### `vision_request`  *(internal only — Acoustic Node → Vision Worker)*
```jsonc
{
  "type": "vision_request",
  "id": "uuid",
  "ts": "ISO8601",
  "trigger_acoustic_id": "uuid",       // links back to the acoustic_event
  "acoustic_confidence": 0.78
}
```

### `vision_event`
```jsonc
{
  "type": "vision_event",
  "id": "uuid",
  "ts": "ISO8601",
  "trigger_acoustic_id": "uuid",
  "adapter": "simulated",              // or "meta_glasses" | "hosted_cv"
  "classification": "drone",           // "drone" | "bird" | "aircraft" | "unknown"
  "confidence": 0.91,
  "bounding_box": { "x": 0.3, "y": 0.2, "w": 0.1, "h": 0.05 }  // null if no detection
}
```

### `fused_assessment`  *(Gateway → Mobile C2 via WebSocket)*
```jsonc
{
  "type": "fused_assessment",
  "id": "uuid",
  "ts": "ISO8601",
  "threat_level": "high",             // "low" | "medium" | "high" | "critical"
  "confidence": 0.86,                 // fused score 0–1
  "acoustic_confidence": 0.78,
  "vision_confidence": 0.91,
  "recommendation": {
    "level": 3,                       // 1=monitor | 2=request_visual | 3=alert_squad | 4=prepare_countermeasures
    "action": "alert_squad",
    "message": "Drone-like signature confirmed visually at 045°. Alert squad.",
    "requires_confirmation": true
  },
  "tracking": {
    "bearing_deg": 45,                // estimated bearing from operator
    "confidence": 0.72,
    "last_updated": "ISO8601"
  }
}
```

### `operator_action`  *(Mobile C2 → Gateway via WebSocket or REST)*
```jsonc
{
  "type": "operator_action",
  "ts": "ISO8601",
  "action": "confirm",                // "acknowledge" | "confirm" | "stand_down" | "escalate"
  "assessment_id": "uuid",            // links to fused_assessment being acted on
  "operator_id": "op-1"
}
```

### `state_snapshot`  *(Gateway → Mobile C2 on connect / GET /state)*
```jsonc
{
  "type": "state_snapshot",
  "ts": "ISO8601",
  "orb_mode": "red",                  // "white" | "red" — drives existing AcousticOrb
  "latest_assessment": { /* fused_assessment */ },
  "reasoning_steps": [ /* task cascade matching existing ReasoningTrail format */ ],
  "scenario_active": true,
  "scenario_id": "demo-alpha"
}
```

---

## Data / Event Flow Direction

```
NOMINAL (listening)
──────────────────
SimAcousticAdapter  ──[AcousticEvent: classification=noise, confidence<0.5]──▶
  Acoustic Node     [below threshold, no vision request]
  Gateway           ──[state_snapshot: orb_mode=white]──▶ Mobile C2

DETECTION CASCADE
─────────────────
SimAcousticAdapter  ──[AcousticEvent: classification=drone_like, conf=0.78]──▶
  Acoustic Node     [threshold crossed]
                    ──[VisionRequest]──▶
                      Vision Worker ──calls──▶ SimVisionAdapter
                      SimVisionAdapter returns VisionEvent{conf=0.91, class=drone}
                    ──[VisionEvent]──▶
                      Fusion Engine
                      Computes: fused_conf = 0.4*acoustic + 0.6*vision = 0.86
                      Selects recommendation level 3
                    ──[FusedAssessment]──▶
  Gateway           ──WebSocket broadcast──▶ Mobile C2
                    Mobile C2: orb turns RED, ReasoningTrail animates cascade,
                               ThreatPanel shows confidence + recommendation,
                               operator sees "Alert squad" + Confirm button

OPERATOR CONFIRMATION
─────────────────────
Mobile C2  ──[OperatorAction: action=confirm]──▶ Gateway
           Gateway logs action, optionally triggers next scenario step
           ──[state_snapshot: updated]──▶ Mobile C2

STAND-DOWN
──────────
Mobile C2 / timeout  ──[OperatorAction: action=stand_down]──▶ Gateway
  Gateway             ──[state_snapshot: orb_mode=white, assessment=null]──▶ Mobile C2
```

---

## Adapter Seams (Simulated → Real Hardware)

Each adapter is a Python ABC. The rest of the system depends only on the interface. Swap the concrete class in `config.py` or via environment variable — no other code changes.

### AcousticAdapter

```python
# adapters/acoustic.py
from abc import ABC, abstractmethod
from typing import Callable, Awaitable
from models import AcousticEvent

class AcousticAdapter(ABC):
    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def subscribe(
        self, callback: Callable[[AcousticEvent], Awaitable[None]]
    ) -> None: ...

# Concrete: SimulatedAcousticAdapter
#   - reads scenario script timing
#   - generates synthetic feature payloads
#   - asyncio.sleep() between events

# Future: RpiAcousticAdapter
#   - opens UDP socket to RPi mic-array agent
#   - streams 50ms frames, computes RMS/FFT in process
#   - emits AcousticEvent on threshold cross
```

### VisionAdapter

```python
# adapters/vision.py
from abc import ABC, abstractmethod
from models import VisionRequest, VisionEvent

class VisionAdapter(ABC):
    @abstractmethod
    async def analyze(self, request: VisionRequest) -> VisionEvent: ...

# Concrete: SimulatedVisionAdapter
#   - returns scripted classification + confidence from scenario
#   - configurable latency (simulates model inference time)

# Future: HostedCVModelAdapter
#   - POSTs JPEG frame to hosted object-detection API
#   - maps response to VisionEvent schema

# Future: MetaGlassesVisionAdapter
#   - pulls latest frame from Meta glasses LiveKit/WebRTC stream
#   - delegates to HostedCVModelAdapter for classification
```

### Injection point

```python
# config.py — single place to swap adapters
ACOUSTIC_ADAPTER = os.getenv("ACOUSTIC_ADAPTER", "simulated")
VISION_ADAPTER   = os.getenv("VISION_ADAPTER", "simulated")

def get_acoustic_adapter() -> AcousticAdapter:
    if ACOUSTIC_ADAPTER == "rpi":
        return RpiAcousticAdapter(host=os.getenv("RPI_HOST"))
    return SimulatedAcousticAdapter()

def get_vision_adapter() -> VisionAdapter:
    if VISION_ADAPTER == "hosted_cv":
        return HostedCVModelAdapter(api_key=os.getenv("CV_API_KEY"))
    return SimulatedVisionAdapter()
```

---

## Recommended Project Structure

```
backend/
├── main.py                    # FastAPI app, lifespan startup
├── config.py                  # Adapter selection, env vars
├── models.py                  # Pydantic event models (all events above)
│
├── adapters/
│   ├── __init__.py
│   ├── acoustic.py            # AcousticAdapter ABC + SimulatedAcousticAdapter
│   └── vision.py              # VisionAdapter ABC + SimulatedVisionAdapter
│
├── core/
│   ├── acoustic_node.py       # Threshold logic, publishes VisionRequest
│   ├── vision_worker.py       # Handles VisionRequest, calls adapter
│   └── fusion.py              # Late fusion math, recommendation policy
│
├── gateway/
│   ├── ws.py                  # WebSocket manager (session registry, broadcast)
│   └── routes.py              # REST endpoints (/state, /scenario, /operator)
│
└── sim/
    ├── engine.py              # Scenario playback orchestrator
    └── scenarios/
        └── demo_alpha.json    # Scripted event timing for end-to-end demo

# Mobile C2 (existing — extend in place)
src/
├── transport/
│   └── useServerEvents.ts     # NEW: WebSocket client hook → feeds zustand store
├── store.ts                   # EXTEND: receive live events, not hardcoded cascade
├── components/
│   ├── AcousticOrb.tsx        # UNCHANGED: consumes mode from store
│   ├── ReasoningTrail.tsx     # EXTEND: driven by server reasoning_steps
│   ├── ThreatPanel.tsx        # NEW: confidence meter + recommendation cards
│   └── TrackingOverlay.tsx    # NEW: simulated bearing indicator
└── screens/
    └── CommandScreen.tsx      # EXTEND: add ThreatPanel + operator action buttons
```

---

## Architectural Patterns

### Pattern 1: Adapter / Port (Hardware Seam)

**What:** Define an ABC interface for each physical input source. The rest of the system never imports the concrete class directly.
**When to use:** Any sensor or external service that will later be replaced by real hardware.
**Trade-offs:** Tiny upfront overhead for interface design; pays back when real RPi/glasses arrive — zero rearchitecting.

```python
# Processing code is always adapter-agnostic:
class AcousticNode:
    def __init__(self, adapter: AcousticAdapter, bus: EventBus): ...
```

### Pattern 2: Internal Event Bus (asyncio Queue)

**What:** Components communicate via a lightweight in-process pub/sub. Each message type has a typed queue. The Gateway is the single external fan-out point.
**When to use:** LAN demo where all backend components run in one Python process. No Kafka/Redis needed.
**Trade-offs:** Simple and fast; doesn't survive multi-process scale-out (not needed for this demo).

```python
class EventBus:
    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    async def publish(self, event_type: str, payload: dict) -> None:
        await self._queues[event_type].put(payload)

    async def subscribe(self, event_type: str) -> dict:
        return await self._queues[event_type].get()
```

### Pattern 3: Late Fusion with Weighted Confidence

**What:** Acoustic confidence and vision confidence are combined as a weighted sum. Vision gets higher weight (it's the confirmation modality). Threshold bands map to threat levels and recommendation escalation.
**When to use:** Always — this is the core domain logic.
**Trade-offs:** Simple and explainable (good for demo). Not a learned model.

```python
def fuse(acoustic_conf: float, vision_conf: float) -> FusedAssessment:
    WEIGHTS = {"acoustic": 0.35, "vision": 0.65}
    fused = acoustic_conf * WEIGHTS["acoustic"] + vision_conf * WEIGHTS["vision"]
    threat_level = (
        "critical" if fused >= 0.85 else
        "high"     if fused >= 0.70 else
        "medium"   if fused >= 0.50 else
        "low"
    )
    return FusedAssessment(confidence=fused, threat_level=threat_level, ...)
```

### Pattern 4: State Snapshot on Connect

**What:** When the mobile C2 opens a WebSocket, the server immediately sends a `state_snapshot` message with current orb mode, latest assessment, and reasoning steps. Subsequent messages are deltas.
**When to use:** Any long-lived WebSocket session where the client might reconnect mid-scenario.
**Trade-offs:** Prevents blank screen on reconnect; minimal extra implementation.

---

## Data Flow: Mobile C2 Integration

The existing store drives the orb via hardcoded `DETECTION_CASCADE` timers. The integration replaces this with live server events while keeping the same data shape — minimising changes to AcousticOrb and ReasoningTrail.

```
Server (FusedAssessment)
    ↓ WebSocket
useServerEvents.ts hook
    ↓ dispatch to zustand
store.ts  (mode, tasks, threat, recommendation)
    ↓ selectors
AcousticOrb  ← mode ("white" | "red")
ReasoningTrail ← tasks[] (same structure, now server-driven)
ThreatPanel  ← threat_level, confidence, recommendation
TrackingOverlay ← tracking.bearing_deg
```

**Key compatibility constraint:** The server's `reasoning_steps` array must match the existing `Task[]` / `Subtask[]` shape in `store.ts` so ReasoningTrail requires no structural changes.

---

## Build Order and Phase Dependencies

```
Phase 1 — Backend Skeleton + Event Schema
│ FastAPI app, Pydantic models (all event types), EventBus, WebSocket manager
│ Deliverable: ws:// endpoint that echoes messages; models validated
│ No adapters yet; no mobile changes
│
Phase 2 — Simulation Layer
│ DEPENDS ON: Phase 1 (event schema, bus)
│ SimulatedAcousticAdapter + SimulatedVisionAdapter
│ Scenario Driver + demo_alpha.json script
│ Acoustic Node + Vision Worker wired up
│ Deliverable: backend prints detection cascade in logs
│
Phase 3 — Fusion Engine + Gateway Routes
│ DEPENDS ON: Phase 2 (events flowing)
│ Fusion math, recommendation policy
│ REST /state, /scenario/start, /operator/action
│ Gateway broadcasts FusedAssessment over WebSocket
│ Deliverable: curl test shows fused events; wscat confirms broadcast
│
Phase 4 — Mobile C2 Integration
│ DEPENDS ON: Phase 3 (WebSocket broadcasting)
│ useServerEvents.ts hook in Expo app
│ store.ts updated to consume live events (DETECTION_CASCADE replaced)
│ ThreatPanel component, operator action buttons
│ Deliverable: app orb turns red on server detection; reasoning trail animates live
│
Phase 5 — Full Demo Polish
│ DEPENDS ON: Phase 4 (full pipeline connected)
│ TrackingOverlay (simulated bearing), scenario start from app
│ End-to-end demo script refined for hackathon presentation
│ Deliverable: repeatable demo scenario runs start-to-finish from one button
```

**Critical path:** Schema → Adapters → Fusion → WebSocket → Mobile integration. Each phase is independently testable before the next begins.

---

## Anti-Patterns

### Anti-Pattern 1: Hardcoding Real Hardware References in Core Logic

**What people do:** `import RPi.GPIO` or `import requests # glasses API` directly in `acoustic_node.py`.
**Why it's wrong:** Breaks on every machine without hardware; no sim possible; can't test in CI.
**Do this instead:** All hardware I/O goes in an adapter. Core logic only sees the ABC.

### Anti-Pattern 2: Replacing the Existing Store Shape

**What people do:** Redesign `store.ts` from scratch to accommodate server events.
**Why it's wrong:** Breaks AcousticOrb and ReasoningTrail which are already polished. Re-renders a working UI.
**Do this instead:** Map server events to the existing `Task[]` / `OrbMode` shape. Add new fields (`threat`, `recommendation`) without changing existing ones.

### Anti-Pattern 3: Polling Instead of WebSocket Push

**What people do:** Mobile app polls `GET /state` every 500ms.
**Why it's wrong:** Latency visible in orb animation; adds load; defeats the real-time UX.
**Do this instead:** Server pushes `fused_assessment` and `state_snapshot` over the already-established WebSocket. REST is only for initial snapshot and operator actions.

### Anti-Pattern 4: Blocking Sync I/O in FastAPI Handlers

**What people do:** `time.sleep()` or `requests.get()` inside an `async def` route.
**Why it's wrong:** Blocks the entire asyncio event loop; WebSocket heartbeats stall.
**Do this instead:** Use `asyncio.sleep()`, `httpx.AsyncClient`, or run blocking calls in `asyncio.run_in_executor`.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Hosted CV model (future) | `httpx.AsyncClient.post()` in `HostedCVModelAdapter` | API key via env var; 5s timeout; returns bounding box + class |
| Meta Glasses feed (future) | WebRTC/LiveKit frame pull or RTSP snapshot in `MetaGlassesVisionAdapter` | Frame extracted, JPEG-encoded, sent to CV model |
| RPi mic array (future) | UDP socket listener in `RpiAcousticAdapter` | RPi streams 50ms PCM frames; adapter computes RMS/FFT locally |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| AcousticAdapter → Acoustic Node | async callback / asyncio Queue | Adapter calls registered `on_event` coroutine |
| Acoustic Node → Vision Worker | asyncio Queue (`vision_request_q`) | Single outstanding request; subsequent acoustic events queue |
| Vision Worker → Fusion Engine | asyncio Queue (`vision_event_q`) | Vision Worker awaits adapter; pushes result |
| Fusion Engine → Gateway | asyncio Queue (`assessment_q`) | Gateway drains queue, broadcasts to all WS sessions |
| Gateway → Mobile C2 | WebSocket JSON text frames | `fused_assessment`, `state_snapshot`, `reasoning_steps` |
| Mobile C2 → Gateway | WebSocket JSON or REST POST | `operator_action` messages |

---

## Sources

- Existing codebase: `src/store.ts`, `src/acoustic/useAcousticDrive.ts`, `App.tsx` — confirms existing data shapes and simulation patterns
- PROJECT.md — defines component requirements, constraints, out-of-scope boundaries
- FastAPI WebSocket docs: https://fastapi.tiangolo.com/advanced/websockets/
- Pydantic discriminated unions: https://docs.pydantic.dev/latest/concepts/unions/
- Python ABC pattern for adapter seams: https://docs.python.org/3/library/abc.html

---

*Architecture research for: Body-worn counter-UAS acoustic-vision C2 (Sentry-CD)*
*Researched: 2026-06-14*
