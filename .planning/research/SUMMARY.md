# Project Research Summary

**Project:** Sentry-CD — Body-Worn Acoustic-Vision Counter-Drone Sentry
**Domain:** Counter-UAS acoustic + vision sensor fusion C2 (simulated demo)
**Researched:** 2026-06-14
**Confidence:** HIGH

---

## Executive Summary

Sentry-CD belongs to a well-studied product category: multi-sensor counter-UAS C2 systems that fuse acoustic and optical evidence into a human-supervised threat assessment. Commercially, this pattern is executed by Dedrone, HENSOLDT Elysion, and DIDIT — all use acoustic/RF detection to cue a camera or radar arm, late-fuse confidence scores, and surface escalating recommendations to a human operator who authorizes each step. The entire pipeline — detection, confirmation, fusion, escalation, tracking — runs as a deterministic cascade where each stage depends strictly on the one before it. This causal chain is both the core demo narrative ("sound finds it, camera confirms it, human acts on it") and the forced build order. There is no shortcut: acoustic must emit calibrated events before vision can trigger; vision results must be typed before fusion can weight them; fusion must publish threat levels before escalation can ladder up; tracking makes no sense before a confirmed threat exists.

The recommended implementation is a single-process Python backend (FastAPI 0.136.3 / uvicorn / asyncio) with all sensor I/O behind ABC adapter seams, wired to the existing Expo / React Native C2 app over a LAN WebSocket. Acoustic feature extraction uses librosa 0.11.0 + scipy (MFCC + spectral bands), vision uses local YOLO11 (`sapoepsilon/yolov11s-drone-detector` via ultralytics 8.4.61) with a `CV_MOCK_MODE` fallback that replays cached responses, and the mobile layer wires directly into the existing zustand store with minimal structural change. This stack is fully offline-capable, avoids rate-limit and latency surprises on demo day, and maps cleanly to the 5-layer architecture (Simulation → Adapters → Processing → Gateway → Mobile C2).

The three risks that can break the demo regardless of code quality are: (1) fusion confidence miscalibration — raw scores from different ML models are not comparable and must be normalized before averaging; (2) a non-repeatable demo scenario — every rehearsal should run an identical scripted event schedule, not a stochastic simulation; and (3) a silent WebSocket disconnect dropping escalation events mid-demo. All three have concrete, low-effort mitigations that must be designed in from day one, not retrofitted.

---

## Key Findings

### Recommended Stack

The entire backend fits in one Python 3.11 process. FastAPI 0.136.3 provides both WebSocket push (sensor/fusion events to the app) and REST (state snapshot, scenario control, operator actions). librosa 0.11.0 extracts MFCC + spectral band features from synthetic audio frames; ultralytics 8.4.61 loads the pre-trained drone YOLO11 model locally so CV inference runs offline. The mobile layer uses the existing Expo SDK 56 / RN 0.85 app — only a `useServerEvents.ts` hook and a `ThreatPanel` component are new. No Redis, no Celery, no multi-worker setup required for a LAN demo.

**Core technologies:**
- **Python 3.11 + FastAPI 0.136.3** — async WebSocket backbone; Pydantic v2 event models; single-process asyncio concurrency
- **librosa 0.11.0 + scipy ≥1.15** — MFCC (n_mfcc=20) + spectral band energy for drone acoustic signature extraction
- **ultralytics 8.4.61** — local YOLO11 drone detector (92.9% precision, ~100ms CPU); pin to this exact version (supply-chain attack in 8.3.41–46)
- **pydantic v2.9+** — typed event schema shared across all pipeline stages; v1 is dead in FastAPI 0.115+
- **reconnecting-websocket 4.4.0** — RN drop-in auto-reconnect with exponential backoff
- **CV_MOCK_MODE** — cached Roboflow/YOLO responses replayed with simulated 400–800ms latency; eliminates API rate-limit risk on demo day

See [STACK.md](.planning/research/STACK.md) for version pins, alternatives considered, and the explicit "what NOT to use" list (PyAudio, pydantic v1, ultralytics 8.3.x, HF InferenceClient for drone models, GStreamer).

### Expected Features

Research confirms the detection cascade is the canonical feature dependency graph for this product class. Every table-stakes feature follows the Acoustic → Vision → Fusion → Escalation → Tracking chain; nothing in the list is optional for a credible demo.

**Must have (table stakes):**
- Simulated acoustic detection with MFCC confidence score + WebSocket `acoustic_event` emission
- Acoustic threshold trigger → vision pipeline handoff (causal parent ID linking both events)
- YOLO vision confirmation with bounding box + `vision_event` over WebSocket
- Late fusion: `fused = 0.35 * acoustic_conf + 0.65 * vision_conf` → 4-level threat enum (low / medium / high / critical)
- 4-stage escalation state machine: IDLE → MONITORING → CONFIRMING → ALERTING → PREPARING
- Human confirm / stand-down UI at every escalation level (DISMISS is as prominent as CONFIRM)
- Agent reasoning trail driven by live server events (not the current scripted DETECTION_CASCADE)
- Simulated target tracking with bearing + mini-map dot after threat confirmation
- Operator action audit log (action, assessment_id, operator_id, ts)
- Sensor status chips (ACOUSTIC / VISION / FUSION / BACKEND: GREEN/YELLOW/RED)
- Scripted scenario player with reset button (identical event sequence every run)
- WebSocket ring buffer (last 20 events) + state snapshot on reconnect

**Should have (competitive differentiators):**
- Bounding-box annotated frame thumbnail in the reasoning trail — the single most compelling visual
- Per-sensor confidence meter (ACOUSTIC bar + VISION bar feeding FUSED THREAT) — demonstrates fusion transparency
- Acoustic-only fallback track when vision times out (label: "ACOUSTIC ONLY")
- Sensor degradation banners ("VISION ONLY" / "ACOUSTIC ONLY") — builds operator trust
- Kalman filter on track position + uncertainty ellipse on mini-map
- Countermeasure option cards (display only, no execution) — shows next steps without autonomous action
- False-alarm scenario rehearsal (operator correctly dismisses) — more compelling than happy-path only

**Defer (v2+):**
- Real RPi microphone and Meta Glasses adapter swap-in
- Multi-target tracking (MTT)
- RF / radar fusion layer
- ROE zone visualization
- Secondary confirmation request workflow
- Event replay / mission replay mode
- RBAC multi-user access control

**Explicit anti-features (never build):**
- Autonomous countermeasure execution — disqualifying; violates HITL constraint
- Live streaming video feed — high bandwidth, distracts from sensor fusion story
- 3D globe / live map tiles — external internet dependency for LAN demo

See [FEATURES.md](.planning/research/FEATURES.md) for the full prioritization matrix (P1/P2/P3) and competitor comparison table.

### Architecture Approach

The system is five layers: Simulation (scripted scenario driver), Adapter (ABC seams for acoustic and vision hardware), Processing (Acoustic Node → Vision Worker → Fusion Engine, wired by asyncio Queues), Gateway (FastAPI WebSocket broadcast + REST), and Mobile C2 (existing Expo app extended with live events). All hardware I/O is behind an ABC interface — the rest of the system never imports a concrete adapter class. The internal event bus is three typed asyncio Queues (`vision_request_q`, `vision_event_q`, `assessment_q`) — no Redis, no Kafka needed for a single-process LAN demo. The mobile integration maps server `reasoning_steps` to the existing `Task[]` / `OrbMode` shape so `AcousticOrb` and `ReasoningTrail` require zero structural changes.

**Major components:**
1. **Scenario Driver** (`sim/engine.py`) — reads `scenarios/demo_alpha.json`, injects acoustic + vision payloads at defined millisecond offsets; deterministic demo playback
2. **AcousticAdapter / VisionAdapter** (ABC + Simulated impls) — config-injected via `ACOUSTIC_ADAPTER` / `VISION_ADAPTER` env vars; future RPi / Meta Glasses adapters drop in here
3. **Acoustic Node** (`core/acoustic_node.py`) — applies SNR-aware threshold + 3/5 persistence window; emits `VisionRequest` with causal `trigger_acoustic_id`
4. **Vision Worker** (`core/vision_worker.py`) — dispatches `VisionRequest` to adapter; enforces 3s timeout; emits `vision_timeout` event on failure (never hangs pipeline)
5. **Fusion Engine** (`core/fusion.py`) — weighted calibrated fusion (35/65 acoustic/vision); maps fused score to threat enum; buffers 2s to wait for vision before emitting
6. **FastAPI Gateway** (`gateway/ws.py` + `gateway/routes.py`) — ConnectionManager with 20-event ring buffer; broadcasts `fused_assessment`; sends `state_snapshot` on every reconnect
7. **Mobile C2** — `useServerEvents.ts` hook → zustand store → `AcousticOrb` + `ReasoningTrail` + new `ThreatPanel` + `TrackingOverlay`

See [ARCHITECTURE.md](.planning/research/ARCHITECTURE.md) for full event schemas, the asyncio Queue wiring diagram, build order, and the four anti-patterns to avoid.

### Critical Pitfalls

1. **Fusion confidence miscalibration** — raw scores from MFCC classifier and YOLO are not on the same probability scale. Pre-define a per-modality calibration lookup table (e.g., acoustic 0.8 → calibrated 0.65) before building the fusion formula, and validate against a 4-scenario matrix (acoustic only, vision only, both, neither). Display `A:0.65 V:0.71 → Fused:0.68` so judges see the reasoning, not a magic number.

2. **Non-repeatable demo scenario** — stochastic simulation produces different confidence trajectories every run. Build a `scenarios/demo_alpha.json` with millisecond-resolution event offsets on day one. Every rehearsal run should be byte-identical. Freeze the script 2 hours before presentation; add a "Reset" button to replay from T=0 without restarting services.

3. **CV_MOCK_MODE missing** — Hosted CV API latency (300–900ms on conference WiFi) and free-tier quota exhaustion can silently kill the vision arm mid-demo. Implement `CV_MOCK_MODE=true` that returns cached bounding-box responses with realistic simulated delay; instrument quota consumption during dev; set a 3s hard timeout with graceful acoustic-only fallback.

4. **WebSocket disconnect drops escalation events** — FastAPI's raw `manager.broadcast()` silently discards events to disconnected clients. Implement a 20-event ring buffer and send the full buffer as `state_sync` on every reconnect. Add 5s server heartbeats; client reconnects if 2 pings are missed.

5. **"Human-in-the-loop" hollow framing** — claiming HITL but showing rubber-stamp confirm buttons damages credibility with technically literate judges. Frame the system as "human-on-the-loop" (supervisory) in all materials. The DISMISS / FALSE ALARM button must be as prominent as CONFIRM. Include a false-alarm scenario in the demo where the operator correctly overrides — this is more impressive than the happy path alone.

See [PITFALLS.md](.planning/research/PITFALLS.md) for the full 14-pitfall catalogue with phase-specific warning map.

---

## Implications for Roadmap

The causal dependency chain — Acoustic → Vision → Fusion → Escalation → Tracking — is not a preference; it is a hard build order. Each phase must produce a verified, independently testable output before the next phase can begin. Five phases are sufficient.

### Phase 1: Backend Skeleton + Acoustic Simulation

**Rationale:** The event schema and WebSocket plumbing must exist before any other component can be built or tested. Acoustic is the root of the detection chain — everything downstream depends on `acoustic_event` having a stable, typed shape. This phase has no external dependencies and no mobile changes required.
**Delivers:** FastAPI app with validated Pydantic event models (all 6 event types), asyncio EventBus, WebSocket ConnectionManager with ring buffer, `SimulatedAcousticAdapter` running the scripted scenario schedule, `AcousticNode` applying SNR-aware threshold and 3/5 persistence window; `ws://` endpoint broadcasting `acoustic_event` and `state_snapshot` on connect.
**Features addressed:** Simulated acoustic detection, WebSocket event emission, scenario player (foundational), sensor status heartbeat.
**Pitfalls avoided:** Pitfall 4 (ring buffer built in from the start), Pitfall 6 (scripted scenario on day one), Pitfall 10 (asyncio discipline from the first file), Pitfall 14 (`.env` + `.gitignore` day one).

### Phase 2: Vision Pipeline + CV Mock

**Rationale:** Vision is triggered by acoustic — it cannot exist before Phase 1 establishes the `VisionRequest` contract. The `CV_MOCK_MODE` must be the primary implementation path; real API integration is a secondary swap. Building mock first forces the interface to be correct without quota risk.
**Delivers:** `VisionAdapter` ABC, `SimulatedVisionAdapter` with `CV_MOCK_MODE` (cached bounding-box responses, configurable latency), `VisionWorker` with 3s timeout and `vision_timeout` graceful fallback; acoustic → vision trigger wired end-to-end; backend logs show the detection cascade.
**Features addressed:** Vision pipeline trigger, drone classification with bounding box, non-drone false-positive class, vision event emission.
**Pitfalls avoided:** Pitfall 5 (CV_MOCK_MODE — never touch real API quota during dev), Pitfall 3 (causal `trigger_acoustic_id` linking events from this phase forward).
**Stack used:** ultralytics 8.4.61 (local YOLO11 loaded in mock's response generator), httpx async client stubbed behind adapter.

### Phase 3: Sensor Fusion + Escalation Engine

**Rationale:** Fusion requires calibrated events from both acoustic and vision arms — only possible after Phase 2. The 4-level threat enum and escalation state machine are the product's core claim and must be correct before any UI work begins. Defining the threat thresholds before building the UI prevents the common trap of tuning confidence values to match a pre-built animation.
**Delivers:** `FusionEngine` with calibrated weighted fusion (35/65 acoustic/vision), 2s vision-wait buffer, threat level enum (low/medium/high/critical), configurable thresholds via env vars; 4-stage escalation state machine (IDLE → MONITORING → CONFIRMING → ALERTING → PREPARING); REST endpoints (`GET /state`, `POST /scenario/{id}/start`, `POST /operator/action`); `fused_assessment` broadcast over WebSocket; operator action audit log.
**Features addressed:** Late fusion, confidence decomposition, null/degraded vision handling, escalation state machine, configurable thresholds, operator confirmation audit log.
**Pitfalls avoided:** Pitfall 2 (calibration lookup table defined here, before any UI renders the numbers), Pitfall 3 (fusion holds buffer until both modalities arrive or timeout), Pitfall 7 (evidence breakdown in every `fused_assessment` payload).
**Stack used:** pydantic v2 discriminated union models, pydantic-settings for env var config.

### Phase 4: Mobile C2 Integration

**Rationale:** The app integration comes after the WebSocket contract is stable — premature mobile work against an unstable schema wastes time. The existing `AcousticOrb` and `ReasoningTrail` are preserved by mapping server events to the existing `Task[]` / `OrbMode` shape. New components (`ThreatPanel`, operator action buttons) are additive.
**Delivers:** `useServerEvents.ts` WebSocket hook with reconnect (replaces DETECTION_CASCADE timers in `store.ts`); `ThreatPanel` with per-sensor confidence meters and 4-level threat display; human CONFIRM + DISMISS + STAND DOWN buttons posting `operator_action` back to gateway; `state_snapshot` rendering on connect/reconnect so orb is never stale; sensor status chips.
**Features addressed:** Live threat state display, escalating recommendation cards, HITL confirmation UI, sensor status indicators, agent reasoning trail driven by live events, alert/haptic on escalation.
**Pitfalls avoided:** Pitfall 9 (DISMISS button as prominent as CONFIRM; human-on-the-loop framing explicit in UI copy), Pitfall 12 (confidence rounded to 1dp via `format_confidence()` utility), Pitfall 13 (Zod runtime validation on all incoming WS messages + ErrorBoundary on ThreatPanel).
**Stack used:** Expo SDK 56 / RN 0.85, existing zustand store, reconnecting-websocket, native WebSocket.

### Phase 5: Target Tracking + Demo Hardening

**Rationale:** Tracking is initiated on ALERT or above — it requires a confirmed fused threat (Phase 3). Demo hardening (Kalman smoothing, uncertainty ellipse, reset button, bounding-box thumbnail, false-alarm scenario) is the final layer and cannot be meaningfully tested until the end-to-end pipeline is live.
**Delivers:** Simulated track (linear/sinusoidal trajectory, configurable speed/heading), track state machine (ACQUIRING → TRACKING → LOST → TERMINATED), track events over WebSocket; `TrackingOverlay` with mini-map dot + heading arrow; Kalman filter position smoothing + uncertainty ellipse radius; bounding-box annotated frame thumbnail in reasoning trail; "Reset Scenario" button (replays from T=0 without restarting services); false-alarm rehearsal scenario (`scenario_02_false_alarm_bird.yaml`).
**Features addressed:** Track initiation, simulated position updates, last-known-position persistence, mini-map display, uncertainty ellipse, bounding-box thumbnail, sensor degradation banners, countermeasure option cards (display only).
**Pitfalls avoided:** Pitfall 1 (false-alarm scenario validates dismiss path), Pitfall 6 (reset button + frozen script 2h before demo), Pitfall 7 (5s dwell before Confirm becomes active after evidence renders).

### Phase Ordering Rationale

- **Schema first, always:** Every subsequent phase depends on a stable `acoustic_event → vision_event → fused_assessment` event chain. Phase 1 locks the schema; phases 2–5 only add new event types, never change existing fields.
- **Adapters before processing:** The ABC seam means Phase 2 (SimulatedVision) can run immediately after Phase 1 without real hardware or API keys.
- **Calibration before UI:** Fusion confidence thresholds (Phase 3) must be defined before any confidence bars are rendered (Phase 4). Building UI first always leads to threshold-tuning to match animation — the confidence number must drive the UI, not the reverse.
- **Mobile last of core:** A stable WebSocket contract (Phase 3 complete) means Phase 4 integration takes hours, not days. Early mobile work against an unstable schema is net negative.
- **Demo hardening is a phase:** Kalman filter, scripted scenario YAML, and reset button are not polish — they are what makes the demo survive live conditions. Deferring them to "the last hour" is how demos fail.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Fusion Engine):** Calibration lookup values (acoustic and YOLO confidence scaling) need empirical tuning against the specific models used. Run the 4-scenario matrix before freezing the formula.
- **Phase 5 (Kalman Filter):** Standard algorithm but parameterisation (process noise Q, measurement noise R) requires iteration against the simulated trajectory. Plan for at least one tuning cycle.

Phases with standard patterns (skip research-phase):
- **Phase 1:** FastAPI WebSocket + asyncio EventBus patterns are thoroughly documented and already sketched in ARCHITECTURE.md. Build directly.
- **Phase 2:** `SimulatedVisionAdapter` is pure Python with no external dependencies. YOLO model loads from HF Hub in one line. No new research needed.
- **Phase 4:** RN WebSocket + zustand wiring is standard; existing store shape is known. ARCHITECTURE.md provides the exact mapping.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI (Jun 2026); supply-chain risk on ultralytics documented and pinned; alternatives explicitly evaluated |
| Features | HIGH | Cross-referenced against 6+ fielded C-UAS systems (Dedrone, HENSOLDT, MidRadar, TrackDeep, SAAB, DIDIT); feature dependency graph validated against domain research |
| Architecture | HIGH | Derived from existing codebase (`store.ts`, `useAcousticDrive.ts`) + established FastAPI WebSocket patterns; component boundaries match PROJECT.md constraints exactly |
| Pitfalls | HIGH (critical) / MEDIUM (moderate) | Critical pitfalls (1–6) corroborated by peer-reviewed papers and official docs; moderate pitfalls from practitioner sources and UNIDIR policy research |

**Overall confidence:** HIGH

### Gaps to Address

- **Fusion calibration values:** The exact temperature scaling or lookup table mapping MFCC classifier output → calibrated probability needs empirical tuning. Treat Phase 3 as the calibration phase; build the 4-scenario test matrix before committing fusion weights to code.
- **YOLO model first-load time:** `sapoepsilon/yolov11s-drone-detector` requires internet access on first `YOLO()` call to download from HF Hub (~19MB). Pre-cache the model weights on the demo machine before the venue; document this in the demo runbook.
- **Conference WiFi vs dedicated hotspot:** Architecture assumes LAN; WebSocket ring buffer and state-sync mitigate brief disconnects. Strongly recommended: run backend on a dedicated mobile hotspot, not conference WiFi, to eliminate the Pitfall 4 trigger entirely.
- **iOS cleartext WS:** Plain `ws://` over LAN works on iOS dev builds. Verify this remains true on the specific iOS version at the venue; add a note to the demo runbook.

---

## Sources

### Primary (HIGH confidence)
- PyPI (fastapi, librosa, ultralytics, sounddevice, pydantic, reconnecting-websocket) — versions verified Jun 2026
- FastAPI official docs (websockets, ConnectionManager pattern) — https://fastapi.tiangolo.com/advanced/websockets/
- HuggingFace Hub: `sapoepsilon/yolov11s-drone-detector` — model metrics, load syntax
- HENSOLDT Elysion C-UAS Mission Core — escalation and kill chain patterns
- MidRadar Integrated Counter-UAV — HITL confirmation and audit log requirements
- SAAB 9LV CUAS CMS datasheet — escalation levels, ROE zones
- hilariie/Counter-UAS (GitHub) — directly comparable simulated C-UAS architecture
- UNIDIR Human–Machine Interfaces in Autonomous Weapon Systems — HITL vs human-on-the-loop framing
- PMC / NCBI 2024: Advances and Challenges in Drone Detection — false positive rates, acoustic feature methods
- AUDRON (arXiv 2512.20407) — MFCC+STFT acoustic feature config, 98.51% accuracy reference
- Grayhill: Human-in-the-Loop HMI for AI-Enabled Defense — HITL design principles

### Secondary (MEDIUM confidence)
- drone-warfare.com: Counter-UAS 101 acoustic detection — operational false positive rates vs lab conditions
- JTIE 2024: Uncertainty-Aware Late Fusion — cross-modal confidence miscalibration analysis
- websocket.org FastAPI guide — ring buffer and reconnect patterns
- Roboflow serverless inference pricing (blog.roboflow.com, Apr 2026) — quota and latency figures
- UNIDIR 2022 — DoD DODI 3000.09 HITL classification reference
- DronePrint acoustic signature / cascaded make-model classification

### Tertiary (LOW confidence)
- getstream.io: Best Practices for Low-Latency Vision AI — 500ms latency heuristic (practitioner, not benchmarked)
- marioottmann.com 2024: Build Demo Infrastructure First — scripted scenario rationale

---
*Research completed: 2026-06-14*
*Ready for roadmap: yes*
