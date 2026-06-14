# Roadmap: Sentry-CD

## Overview

Five phases that follow the hard causal build order imposed by the sensor fusion pipeline: the backend skeleton and event schema must exist before any sensor can publish; acoustic simulation must work before vision can be triggered; both modalities must be flowing before fusion can calibrate and escalate; the WebSocket contract must be stable before the mobile C2 is wired; and tracking plus demo hardening are the final layer that make the end-to-end scenario survive live demo conditions. The existing Expo / React Native C2 app is extended — not rebuilt — throughout.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Backend Skeleton + Acoustic Simulation** - FastAPI backbone, Pydantic event schema, WebSocket manager with ring buffer, simulated acoustic pipeline, scenario player
- [x] **Phase 2: Vision Pipeline + CV Mock** - Vision adapter seam, SimulatedVisionAdapter with CV_MOCK_MODE, acoustic→vision trigger wired end-to-end
- [x] **Phase 3: Fusion Engine + Escalation** - Calibrated late fusion, 4-level threat enum, escalation state machine, operator confirmation REST + audit log
- [ ] **Phase 4: Mobile C2 Integration** - useServerEvents hook, live zustand store, ThreatPanel, CONFIRM/DISMISS controls, sensor status chips
- [ ] **Phase 5: Target Tracking + Demo Hardening** - Simulated target track, mini-map overlay, reset button, false-alarm scenario, full end-to-end run

## Phase Details

### Phase 1: Backend Skeleton + Acoustic Simulation
**Goal**: The event schema is locked and the WebSocket backbone is live; the acoustic node emits calibrated detection events from a scripted scenario schedule that any downstream component can consume
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: ACO-01, ACO-02, ACO-03, ACO-04, ACO-05, SYS-01, SYS-02
**Success Criteria** (what must be TRUE):
  1. The FastAPI server starts and accepts WebSocket connections; a connecting client receives a `state_snapshot` within 1 second
  2. Running the scenario player sends a timed sequence of `acoustic_event` messages visible in server logs with classification and confidence fields
  3. A WebSocket client (`wscat` or the app) receives `acoustic_event` broadcasts during an active scenario run
  4. After a simulated disconnect, a reconnecting client receives the last 20 events as `state_sync` replay before new events resume
**Plans**: TBD

### Phase 2: Vision Pipeline + CV Mock
**Goal**: An acoustic detection event triggers the vision confirmation pipeline; the vision adapter returns a typed result with causal linkage to the acoustic trigger, with CV_MOCK_MODE keeping the pipeline offline-safe
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: VIS-01, VIS-02, VIS-03, VIS-04
**Success Criteria** (what must be TRUE):
  1. A qualifying acoustic event causes a `vision_event` to appear in server logs with a `trigger_acoustic_id` linking it to the source acoustic event
  2. With `CV_MOCK_MODE=true`, the vision pipeline returns a cached bounding-box response with realistic latency and makes zero real API calls
  3. When the vision adapter exceeds the 3-second timeout, the backend emits a `vision_timeout` event and the pipeline continues without hanging
**Plans**: TBD

### Phase 3: Fusion Engine + Escalation
**Goal**: Acoustic and visual confidence are fused into a calibrated 4-level threat assessment; the escalation state machine advances only on human confirmation; operator actions are logged to an audit trail
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: FUS-01, FUS-02, FUS-03, FUS-04, ESC-01, ESC-02, ESC-03, ESC-04, ESC-05
**Success Criteria** (what must be TRUE):
  1. A `fused_assessment` WebSocket message is broadcast after each detection cascade, showing `acoustic_confidence`, `vision_confidence`, and `fused` scores with per-source breakdown visible to the operator
  2. The threat level advances correctly through all 4 levels (low → medium → high → critical) as fused confidence rises across the scripted scenario
  3. When vision is unavailable, the fused assessment is labeled "ACOUSTIC ONLY" with a threat level capped below CRITICAL
  4. Operator confirm and stand-down actions sent to `POST /operator/action` are accepted, change the escalation state, and appear in the append-only audit log
**Plans**: TBD

### Phase 4: Mobile C2 Integration
**Goal**: The existing Expo C2 app is extended with a live WebSocket connection that drives the Skia orb, reasoning trail, and new ThreatPanel from server events — replacing the hardcoded DETECTION_CASCADE timers — with CONFIRM and DISMISS controls that post back to the gateway
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06
**Success Criteria** (what must be TRUE):
  1. The Skia orb transitions from white to red when the server emits a high-confidence `fused_assessment`, driven by live WebSocket — the hardcoded DETECTION_CASCADE timer is removed
  2. The reasoning trail animates the live acoustic → vision → fusion evidence chain from server `reasoning_steps`, not from any scripted cascade in the client
  3. ThreatPanel displays the 4-level threat state, fused confidence (rounded to 1 decimal place), and the current escalation recommendation card with the consequence labelled
  4. Tapping CONFIRM or STAND DOWN sends an `operator_action` to the backend and the UI updates accordingly; DISMISS is as visually prominent as CONFIRM
  5. Subsystem status chips (acoustic, vision, fusion, backend) reflect live health state; a new escalation triggers haptic + visual alert
**Plans**: TBD
**UI hint**: yes

### Phase 5: Target Tracking + Demo Hardening
**Goal**: A simulated target track appears on the mini-map after threat confirmation; the complete end-to-end demo scenario runs start-to-finish deterministically with a reset button; a false-alarm path exercises the operator's DISMISS authority
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: TRK-01, TRK-02, TRK-03, SYS-03
**Success Criteria** (what must be TRUE):
  1. After the operator confirms a threat, a target track appears on the mini-map with a bearing indicator that moves along the simulated trajectory; track lifecycle (acquiring → tracking → lost) is reflected in the UI
  2. The "Reset Scenario" button replays the full demo from T=0 without restarting backend services
  3. A complete simulated run (acoustic detect → vision confirm → fusion → escalation → human confirm → tracking) completes with consistent, deterministic event timing every run
  4. The false-alarm scenario (bird detection) runs end-to-end, and the operator's DISMISS action correctly resets the system to monitoring state
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Backend Skeleton + Acoustic Simulation | 0/TBD | Not started | - |
| 2. Vision Pipeline + CV Mock | 0/TBD | Not started | - |
| 3. Fusion Engine + Escalation | 0/TBD | Not started | - |
| 4. Mobile C2 Integration | 0/TBD | Not started | - |
| 5. Target Tracking + Demo Hardening | 0/TBD | Not started | - |
