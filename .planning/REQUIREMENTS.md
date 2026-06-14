# Requirements: Sentry-CD

**Defined:** 2026-06-14
**Core Value:** When a drone-like sound is detected, the operator gets a fused (sound + vision) confidence-scored threat assessment and a clear, escalating recommendation — fast, with the human always in control of the final action.

## v1 Requirements

Requirements for the initial demo release (full fused alert flow, simulated end-to-end). Each maps to a roadmap phase.

### Acoustic Detection

- [x] **ACO-01**: The acoustic node continuously samples a (simulated) audio stream and windows it into frames
- [x] **ACO-02**: The system extracts spectral features and classifies each window as drone-like vs not, with a 0.0–1.0 confidence
- [x] **ACO-03**: Temporal/SNR-aware gating suppresses spurious detections (confidence must persist over N windows before triggering downstream)
- [x] **ACO-04**: Acoustic detections are emitted as structured events over the WebSocket backbone
- [x] **ACO-05**: The acoustic input sits behind a swappable adapter (simulated now, real Raspberry Pi mic later)

### Vision Confirmation

- [x] **VIS-01**: A qualifying acoustic detection triggers the vision confirmation pipeline (vision does not run continuously)
- [x] **VIS-02**: The vision layer classifies the POV frame via a pretrained model and returns a label + 0.0–1.0 confidence
- [x] **VIS-03**: Vision results are emitted as structured events over the WebSocket backbone, causally linked to the triggering acoustic event
- [x] **VIS-04**: The POV video input sits behind a swappable adapter (simulated frames now, Meta glasses later) with a CV mock mode for offline/demo reliability

### Sensor Fusion

- [x] **FUS-01**: Late fusion combines acoustic + visual confidence into a calibrated fused confidence
- [x] **FUS-02**: Fused confidence maps to a 4-level threat enum (MONITOR → CAUTION → ALERT → CRITICAL) with configurable thresholds
- [x] **FUS-03**: Every fusion event includes the per-source breakdown (acoustic, vision, fused)
- [x] **FUS-04**: Fusion degrades gracefully to an acoustic-only track when vision is unavailable/low-confidence (threat level capped, state labeled "ACOUSTIC ONLY")

### Escalation & Human-in-the-Loop

- [x] **ESC-01**: An escalation state machine advances the threat through 4 levels, driven by fusion events
- [x] **ESC-02**: Each level presents a specific operator recommendation (monitor → request secondary confirmation → alert squad → prepare countermeasure options)
- [x] **ESC-03**: Advancing an escalation requires explicit human confirmation; the system never auto-engages
- [x] **ESC-04**: The operator can stand down / cancel at any level, resetting the system to monitoring
- [x] **ESC-05**: Operator confirmations and stand-downs are recorded to an append-only audit log (action, level, timestamp)

### Target Tracking

- [x] **TRK-01**: On threat confirmation, a target track is initiated with a track ID and last-known position
- [x] **TRK-02**: Simulated target position updates stream over WebSocket and drive the operator mini-map
- [x] **TRK-03**: Track lifecycle states reflected to operator (acquiring → tracking → lost, exercised by the sim when a closing target passes through minimum range)

### Operator Interface

- [x] **UI-01**: The C2 app displays the live threat level + fused confidence (existing Skia orb extended to 4 threat states)
- [x] **UI-02**: The C2 app shows subsystem status indicators (acoustic, vision, fusion, backend)
- [x] **UI-03**: The agent reasoning trail renders the live evidence chain from server events (replacing the scripted cascade)
- [x] **UI-04**: Escalating recommendation cards present confirm + stand-down controls
- [~] **UI-05**: A new escalation alerts the operator (visual: orb red + threat-colored badge/cards ✓; haptics + sound deferred — needs `expo-haptics` native dep + dev-build rebuild)
- [x] **UI-06**: A mini-map shows the simulated target's position and heading

### Backbone & Demo

- [x] **SYS-01**: A FastAPI + WebSocket gateway broadcasts events to connected clients with a replay/ring buffer + state-sync on reconnect
- [x] **SYS-02**: A scripted scenario player drives a deterministic, repeatable end-to-end demo run
- [x] **SYS-03**: A full simulated scenario runs start to finish (acoustic → vision → fusion → escalation → human confirmation → tracking)

## v2 Requirements

Deferred. Tracked but not in the current roadmap.

### Vision & Evidence

- **VIS-05**: Bounding-box annotated frame thumbnail surfaced in the reasoning trail ("visual proof")
- **VIS-06**: Object trajectory hint from consecutive frames feeding tracking

### Fusion & Tracking Sophistication

- **FUS-05**: Bayesian/probabilistic fusion instead of fixed weighted average
- **TRK-04**: Kalman filter position smoothing
- **TRK-05**: Uncertainty ellipse visualization on the mini-map (grows on sensor degradation)

### Interface Polish

- **UI-07**: Per-sensor confidence meters (acoustic + vision feeding fused bar)
- **UI-08**: Sensor degradation banners ("VISION ONLY" / "ACOUSTIC ONLY")
- **UI-09**: Countermeasure option cards (display-only, human-tap required)
- **UI-10**: Event replay / mission history scroll

### Acoustic Sophistication

- **ACO-06**: Cascaded drone make → model classification (multi-class output)

### Hardware Enablement

- **HW-01**: Real Raspberry Pi microphone adapter swap-in
- **HW-02**: Real Meta Glasses POV feed adapter swap-in

## Out of Scope

Explicitly excluded to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Autonomous countermeasure / weapon engagement | Ethical/safety hard line — human authorizes every action; autonomous fire is disqualifying |
| Real RPi / Meta-glasses hardware integration | Simulated this milestone; adapter seams keep it swappable later |
| RF / radar sensor fusion | No RF/radar hardware or simulation; architecture stays sensor-agnostic |
| Multi-target tracking (MTT) | Track-association complexity; demo uses a single simulated target |
| Live video streaming in the C2 app | High bandwidth/latency over LAN; annotated still + box tells the same story |
| Multi-user RBAC / auth | Single-operator demo; zero demo value for the cost |
| External push (SMS/squad notify) | LAN-local demo; narrate as future integration |
| 3D globe / live map tiles | Requires network/tile server; static 2D tactical mini-map suffices |
| Localization / theme switching | No demo value vs. effort |

## Traceability

Populated during roadmap creation. Each v1 requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ACO-01 | Phase 1 | Done |
| ACO-02 | Phase 1 | Done |
| ACO-03 | Phase 1 | Done |
| ACO-04 | Phase 1 | Done |
| ACO-05 | Phase 1 | Done |
| VIS-01 | Phase 2 | Done |
| VIS-02 | Phase 2 | Done |
| VIS-03 | Phase 2 | Done |
| VIS-04 | Phase 2 | Done |
| FUS-01 | Phase 3 | Done |
| FUS-02 | Phase 3 | Done |
| FUS-03 | Phase 3 | Done |
| FUS-04 | Phase 3 | Done |
| ESC-01 | Phase 3 | Done |
| ESC-02 | Phase 3 | Done |
| ESC-03 | Phase 3 | Done |
| ESC-04 | Phase 3 | Done |
| ESC-05 | Phase 3 | Done |
| TRK-01 | Phase 5 | Done |
| TRK-02 | Phase 5 | Done |
| TRK-03 | Phase 5 | Done |
| UI-01 | Phase 4 | Done |
| UI-02 | Phase 4 | Done |
| UI-03 | Phase 4 | Done |
| UI-04 | Phase 4 | Done |
| UI-05 | Phase 4 | Partial (visual ✓, haptics/sound deferred) |
| UI-06 | Phase 4 | Done |
| SYS-01 | Phase 1 | Done |
| SYS-02 | Phase 1 | Done |
| SYS-03 | Phase 5 | Done |

**Coverage:**
- v1 requirements: 30 total
- Fully delivered: 29 ✓
- Partial: 1 (UI-05 — visual alerting done; haptics/sound deferred, needs native rebuild)
- Mapped to phases: 30 ✓

---
*Requirements defined: 2026-06-14*
*Last updated: 2026-06-14 after milestone v1 build (all 5 phases shipped)*
