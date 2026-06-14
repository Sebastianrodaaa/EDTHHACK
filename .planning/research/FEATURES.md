# Feature Research — Sentry-CD Counter-UAS C2

**Domain:** Body-worn acoustic + vision counter-drone early-warning command-and-control (C2)
**Researched:** 2026-06-14
**Confidence:** HIGH (acoustic, fusion, C2 patterns); MEDIUM (demo-specific simulation features)

---

## Feature Landscape

Features are organized by subsystem: **Acoustic Detection**, **Vision Confirmation**, **Sensor Fusion / Threat Assessment**, **Escalation & Human-in-the-Loop C2**, **Target Tracking**, and **Operator Interface**.

---

### 1. Acoustic Detection

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Continuous audio capture + frame windowing | All acoustic C-UAS systems require constant listening; silent gaps = missed detections | LOW | Rolling buffer of ~1-2 s windows (standard: 256–512 ms hop); simulated via synthetic audio generator |
| Feature extraction (MFCC / spectral) | MFCC is the industry baseline feature for acoustic drone classification; without it the classifier has no meaningful input | LOW–MEDIUM | MFCC + STFT spectrogram; scipy / librosa; ~240 ms latency achievable |
| Drone vs. non-drone binary classification | Minimum credible detection output — "is this a drone?" | MEDIUM | KNN or lightweight CNN on MFCC; >95% accuracy on clean audio achievable |
| Confidence score per detection window | Evaluators and demo observers need a number, not just a binary flag | LOW | 0.0–1.0 score; aggregated over rolling window of N frames (e.g., 5/8 majority) |
| SNR-aware adaptive threshold | False positives from wind / road noise kill operator trust; threshold must adapt to noise floor | MEDIUM | Raise threshold when SNR < 20 dB; standard practice in fielded acoustic sensors (Dedrone, AALIS) |
| Detection event emission via WebSocket | The backbone is FastAPI + WebSocket; the acoustic node must publish structured events | LOW | `{event: "acoustic_detection", confidence: 0.82, snr_db: 24.1, ts: ...}` |
| Simulated audio source adapter | Hardware-absent hackathon; real RPi mic must be swappable in later | LOW | Interface + SyntheticAudioSource implementation; injectable via config |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Drone model / type classification | Distinguishes DJI Mavic from FPV racer — higher threat specificity, more compelling demo | MEDIUM | Multi-class classifier; pre-trained on public datasets (DronePrint, AUDRON); adds credibility |
| Cascaded detection: make → model | Mirrors DronePrint's two-stage ID — "quadcopter → DJI Mavic 3" is a convincing demo narrative | MEDIUM | Two sequential classifiers; only triggers model-ID if make is confirmed |
| Persistent detection history with replay | Operators need to review past events; mission replay is a standard C-UAS C2 feature (HENSOLDT Elysion) | MEDIUM | Timestamped event log; replayable in the app |

#### Anti-Features (Acoustic)

| Feature | Why Requested | Why Skip | Alternative |
|---------|---------------|----------|-------------|
| Microphone array / beamforming | Adds directionality and range | Hardware not guaranteed; massive complexity for demo value | Single-mic simulation is sufficient; note capability gap honestly in demo |
| Full open-set unknown-drone detection | "What if it's a drone we've never seen?" | Open-set classification requires large, diverse libraries and specialized architectures (DronePrint open-set: 86% vs 96% closed-set); adds weeks | Closed-set binary + a clearly labeled "UNKNOWN" fallback class; flag in demo as future work |
| Real-time SNR estimation from field acoustics | Genuine noise floor measurement | No real mic = meaningless; simulation fakes it | Simulated SNR values injected by the synthetic audio source |

---

### 2. Vision Confirmation

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Vision pipeline triggered by acoustic event | The core product concept — acoustic → visual handoff; every real C-UAS system (DIDIT, L3Harris Drone Guardian) does acoustic/radar → camera slew | LOW | Acoustic event triggers vision pipeline; simulated by synthetic frame source |
| Drone classification on frame / clip | Visual confirmation must produce a label + confidence; "visually confirmed drone" is the key demo beat | MEDIUM | Hosted pre-trained model (Roboflow, Hugging Face YOLO-v8 / RT-DETR); REST or streaming API call |
| Classification confidence score | Required for late fusion; operator needs to see both acoustic and visual confidence | LOW | 0.0–1.0; returned from hosted CV model |
| Simulated POV video source adapter | Meta glasses are not available; must simulate a POV feed with injected drone frames | LOW | SyntheticVideoSource: synthetic frames or pre-recorded clip with drone at configurable timestamp |
| Vision event emission via WebSocket | Same event backbone; vision must publish structured results | LOW | `{event: "vision_result", label: "drone", confidence: 0.91, frame_ts: ...}` |
| Non-drone / false-positive class | Vision must distinguish drone from bird, aircraft, debris to reduce operator alert fatigue | MEDIUM | Use model with "bird", "aircraft", "background" classes; YOLO models trained on drone datasets already include these |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Bounding-box + annotated frame in the app | Visual proof — the operator sees the box around the drone in the POV frame; enormously compelling for a demo | MEDIUM | Return bounding box coords with vision result; render overlay in RN app or embed image thumbnail |
| Visual confidence uncertainty display | Show decreasing confidence as simulated "drone moves out of frame" — demonstrates robust system behavior | LOW | Simulated by varying synthetic frame content over time |
| Object trajectory hint from consecutive frames | Frame-to-frame delta in bounding box gives motion vector — feeds target tracking | MEDIUM | Lightweight; optical flow or box-center delta between frames |

#### Anti-Features (Vision)

| Feature | Why Requested | Why Skip | Alternative |
|---------|---------------|----------|-------------|
| Live streaming video feed in C2 app | Feels immersive | High bandwidth / latency over LAN; complex buffering; distracts from the sensor fusion story | Show annotated thumbnail / still frame + bounding box; conveys the same information cleanly |
| Custom-trained drone detection model | Maximum accuracy for this specific drone type | Training data curation + fine-tuning is weeks of work; hosted pretrained models (YOLOv8-drone, RF100) are highly capable | Use hosted API (Roboflow Inference, HF inference endpoint) with a strong pretrained checkpoint |
| Multi-camera / multiple POV feeds | Broader coverage | Demo has one body-worn POV; multi-camera requires complex mux logic | Single simulated POV; architecture is extensible |

---

### 3. Sensor Fusion / Threat Assessment

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Late fusion of acoustic + visual scores | The core technical claim of Sentry-CD; this is what every fielded system does (Dedrone, DIDIT, HENSOLDT Elysion) | MEDIUM | Weighted average or product rule: `fused = w_a * acoustic_conf + w_v * vision_conf`; simple and explainable |
| Fused threat level (enum + score) | C-UAS operators think in MONITOR / CAUTION / THREAT / CRITICAL; raw numbers are not actionable | LOW | Map fused score to 4-level threat enum with configurable thresholds |
| Confidence decomposition (source breakdown) | Operators must understand why the system raised an alert (accountability, HITL compliance); SAAB, MidRadar all log per-sensor contributions | LOW | Include `{acoustic_conf, vision_conf, fused_conf, threat_level}` in every fusion event |
| Fusion event published via WebSocket | Downstream consumers (C2 app, tracking, recommendations) subscribe to fusion events | LOW | `{event: "fusion_result", threat_level: "THREAT", fused_conf: 0.88, ...}` |
| Null / degraded vision handling | Vision pipeline may time out or return low confidence; fusion must remain valid with acoustic-only evidence | LOW | If vision_conf < threshold or vision unavailable: weight falls back to acoustic-only track; label state as "ACOUSTIC ONLY" |
| Configurable fusion weights | Demo tuning: can dial up visual weight to see threat level drop when vision is uncertain | LOW | `ACOUSTIC_WEIGHT` / `VISION_WEIGHT` env vars; default 0.4 / 0.6 (vision slightly more trusted post-confirmation) |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Bayesian / probabilistic fusion (vs. weighted average) | More defensible than fixed weights; updates belief as evidence arrives; demonstrates technical sophistication | HIGH | Naïve Bayes sensor fusion; uses prior drone-in-area probability; good demo talking point but optional |
| Fusion state timeline / evidence trail | Show the reasoning chain: acoustic triggered → vision confirmed → confidence rose → THREAT declared; already exists as "agent reasoning trail" in the current app | LOW | Serialize state transitions as a timestamped list; render as the existing reasoning trail component |
| False positive suppression via temporal gating | Require acoustic confidence to persist for ≥ N frames before triggering vision; industry standard (AALIS uses 5/8 majority window) | LOW–MEDIUM | `ACOUSTIC_TRIGGER_THRESHOLD` = 0.65 sustained over 3/5 windows before vision fires |

#### Anti-Features (Fusion)

| Feature | Why Requested | Why Skip | Alternative |
|---------|---------------|----------|-------------|
| RF / radar fusion | "Real" multi-sensor systems include RF / radar | No RF / radar hardware or simulation; adds nothing to demo story | Describe as a planned layer in the demo narrative; architecture is sensor-agnostic |
| Fully automated mitigation decision | "Close the loop" | Violates core constraint — human must authorize all actions | Automated recommendations with mandatory human confirmation step |

---

### 4. Escalation & Human-in-the-Loop C2

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 4-level threat escalation state machine | Industry standard for C-UAS C2: MONITOR → CAUTION / CONFIRM → ALERT → PREPARE (MidRadar, SAAB, HENSOLDT); missing = system feels undifferentiated | LOW | `IDLE → MONITORING → CONFIRMING → ALERTING → PREPARING`; driven by fusion events |
| Escalating human-confirmable recommendations | Each threshold transition must present a specific, human-actionable recommendation — not just an alarm | LOW | "Drone-like sound detected — keep observing" → "Vision confirming — request secondary?" → "Drone confirmed — alert squad" → "High confidence threat — review countermeasure options" |
| Human confirmation tap before advancing to next level | Core HITL requirement; MidRadar explicitly states "all mitigation operations require human confirmation"; no escalation without operator acknowledgment | LOW | Modal / bottom-sheet confirm action in app; backend records operator_id + timestamp per confirmation |
| Recommendation + confirmation audit log | Legal / accountability requirement in real C-UAS (MidRadar records operator and timestamp per authorization); essential for a credible demo | LOW | Append-only log: `{level, recommendation, confirmed_by, ts}` |
| Operator "cancel / stand down" at any escalation level | Operators must be able to stop at any point (MidRadar: "response process can be stopped at any time") | LOW | "Stand Down" button always visible; resets to MONITORING |
| Configurable escalation thresholds | Different environments need different sensitivity; makes the demo tunable | LOW | Env vars: `MONITOR_THRESHOLD`, `CAUTION_THRESHOLD`, `ALERT_THRESHOLD` |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Countermeasure option menu (display only) | Shows available non-kinetic options (jammer, net launcher, alert perimeter) as selectable cards — demonstrates system knows next steps without allowing autonomous action | LOW | Read-only option cards with metadata (type, effectiveness, range); no execution backend |
| Secondary confirmation request workflow | Operator can flag "request second opinion" — simulates multi-operator coordination; demonstrates that the system supports team decision-making | MEDIUM | Broadcast a `secondary_confirmation_requested` event; demo shows it as a pending indicator |
| Rules of engagement (ROE) zone display | Visual representation of "this zone is active / restricted / permissive" on a mini-map; SAAB CUAS CMS explicitly supports ROE zones | MEDIUM | Static simulated zone overlay on the mini-map; zone type affects recommendation text |

#### Anti-Features (Escalation / HITL)

| Feature | Why Requested | Why Skip | Alternative |
|---------|---------------|----------|-------------|
| **Autonomous weapon engagement / auto-countermeasure execution** | "Full kill chain" | Explicitly out of scope — ethical/safety constraint; any demo that fires a countermeasure autonomously is disqualifying | Show countermeasure option cards + require human tap; narrate in demo that engagement requires separate physical authorization |
| Multi-user role-based access control (RBAC) | Realistic operational multi-user system | Demo is single-operator; RBAC adds auth complexity with zero demo value | Note as a future architectural layer; simple `operator_id` token is sufficient |
| Push notifications to external systems | Alert squad via SMS / push | Network complexity; demo is LAN-local | Show in-app alert badge + audio; narrate external notification as a future integration |

---

### 5. Target Tracking

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Track initiation on threat confirmation | Once fusion confirms a drone, it must be tracked — all C-UAS C2 systems maintain a track after positive ID (DIDIT, HENSOLDT) | LOW | Assign track ID; record last known position, bearing, timestamp |
| Simulated target position update | Demo needs a moving target; static track is unconvincing | LOW | Linear / sinusoidal trajectory simulation; configurable speed + heading; published via WebSocket |
| Track state machine (ACQUIRING → TRACKING → LOST → TERMINATED) | Standard track lifecycle for operator situational awareness | LOW | State transitions on position update gaps; `LOST` after N seconds without update |
| Last-known-position persistence | If tracking signal is lost, operator needs to know where target was last seen | LOW | Store last confirmed `{lat, lon, altitude, ts}` in track record |
| Track events published via WebSocket | C2 app subscribes to track events for mini-map updates | LOW | `{event: "track_update", track_id, state, position, heading, speed, confidence}` |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Kalman filter position smoothing | Industry standard (hilariie/Counter-UAS, L3Harris) for noisy position estimates; demonstrates technical rigor | MEDIUM | 2D Kalman filter on simulated position stream; visibly reduces "jitter" on mini-map |
| Uncertainty ellipse visualization | Confidence circle on mini-map grows when sensor degrades (RADAR DOWN demo beat from hilariie/Counter-UAS) — highly compelling visual | MEDIUM | Covariance from Kalman filter → rendered as ellipse; balloon animation when vision lost |
| Projected intercept heading arrow | Shows where drone is heading on mini-map; makes the threat feel dynamic and urgent | LOW | Arrow from track position along current heading vector; simple trigonometry |

#### Anti-Features (Tracking)

| Feature | Why Requested | Why Skip | Alternative |
|---------|---------------|----------|-------------|
| Multi-target tracking (MTT) | "What if there are multiple drones?" | Adds track association complexity (JPDA, MHT algorithms); demo has one simulated target | Architecture supports multiple track IDs but demo uses one; note MTT as future work |
| Pilot/GCS geolocation | Find the drone operator's position | Requires RF triangulation hardware and algorithms; entirely out of scope | Note as a future RF-layer capability |
| Predictive intercept geometry | Compute intercept solution | Implies countermeasure dispatch; violates HITL constraint | Show projected heading only; no intercept solution |

---

### 6. Operator Interface (Mobile C2 App)

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Live threat state display (current threat level + confidence) | Central requirement: operator must know current system state at a glance | LOW | Already partially implemented (Skia acoustic orb, white/red state); extend to 4-level color coding |
| Sensor status indicators (acoustic, vision, fusion, backend) | Operators need to know if the system itself is healthy; dead sensor ≠ safe sky (counteruavradar.com C2 design guide) | LOW | Status chips for each subsystem: GREEN / YELLOW / RED; driven by heartbeat events |
| Agent reasoning trail (evidence chain display) | Shows the chain of evidence: acoustic → vision → fusion → recommendation; existing component in the app | LOW | Already exists as "scripted detection-cascade reasoning trail"; connect to live events |
| Escalating recommendation cards | Each escalation level shows a clear, actionable recommendation card | LOW | Card per threat level with recommendation text + confirm / stand-down buttons |
| Human confirmation UI (confirm / stand-down buttons) | HITL requirement; must be obvious and impossible to trigger accidentally | LOW | Large primary button (confirm) + secondary (stand down); confirmation modal with threat summary |
| Alert / notification on new escalation | Operator may not be actively watching the screen; needs audio + visual alert | LOW | Expo haptics + in-app sound on escalation level change |
| Mini-map with target position and track | Situational awareness cornerstone; all C-UAS C2 systems show a map (TrackDeep, HENSOLDT Elysion, hilariie demo) | MEDIUM | Simple top-down 2D mini-map; target dot + heading arrow; no live map tile dependency required for demo |
| Acoustic orb state visualization (existing) | Already built; shows live audio confidence level and state | LOW | Extend existing Skia Liquid Glass orb to animate on all 4 threat levels, not just white/red |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Bounding-box frame thumbnail at vision confirmation | "Here is the visual proof" — most compelling single demo element; rare in mobile C-UAS interfaces | MEDIUM | Small thumbnail with YOLO bounding box overlay; pushed with fusion event; renders in reasoning trail |
| Confidence meter per sensor (acoustic + visual) | Shows both input confidences, not just the fused score; demonstrates sensor fusion transparency (Royal Military Academy HMI study: "clear presentation of uncertainty") | LOW | Two horizontal progress bars labeled "ACOUSTIC" / "VISION" feeding into "FUSED THREAT"; animated |
| Uncertainty ellipse on mini-map (Kalman covariance) | Grows when tracking degrades; shrinks on re-acquisition; viscerally communicates system uncertainty | MEDIUM | Animated circle radius mapped to position covariance estimate |
| Event replay / history scroll | Operator can review what happened; mission replay is a standard C-UAS feature (HENSOLDT, TrackDeep) | LOW | Scrollable timestamped event log; already partially present as reasoning trail |
| Sensor degradation "VISION ONLY / ACOUSTIC ONLY" banner | Shows system is still operating despite partial sensor failure; builds operator trust | LOW | Conditional banner driven by sensor status events; same pattern as hilariie/Counter-UAS radar-down UI |

#### Anti-Features (Operator Interface)

| Feature | Why Requested | Why Skip | Alternative |
|---------|---------------|----------|-------------|
| Live streaming video in the app | Immersive "see what the soldier sees" | High bandwidth, buffer management, encoding pipeline; net contribution to demo < cost; blurs the sensor fusion story | Annotated still frame + bounding box + confidence score tells the same story cleanly |
| 3D globe / live map tiles | Impressive visual | Requires internet / map tile server; demo is LAN-local; adds infrastructure dependency | Static 2D tactical mini-map with range rings; no external dependencies |
| Multi-language / localization | Professional product polish | Zero demo value; considerable i18n overhead | English-only for hackathon |
| Complex settings / configuration UI | Operator adjustability | Out of scope for demo; config lives in env vars | Note as future work |
| Dark mode / theme switching | UX polish | Marginal value vs. effort; existing app has one theme | Keep existing theme |

---

## Feature Dependencies

```
[Acoustic Detection]
    └──triggers──> [Vision Confirmation]
                       └──feeds──> [Sensor Fusion / Threat Assessment]
                                       └──drives──> [Escalation State Machine]
                                                       └──controls──> [Operator Recommendations]
                                                       └──initiates──> [Target Tracking]

[Target Tracking]
    └──feeds──> [Mini-map Display]
    └──requires──> [Sensor Fusion] (track initiation gated on threat confirmation)

[Sensor Fusion]
    └──requires──> [Acoustic Detection] (minimum viable fusion input)
    └──enhanced-by──> [Vision Confirmation] (raises fused confidence)

[Agent Reasoning Trail]
    └──requires──> [Fusion Events + Escalation Events] (live event stream)

[Bounding-box Frame Thumbnail]
    └──requires──> [Vision Confirmation] (bounding box comes from CV model response)

[Kalman Filter / Uncertainty Ellipse]
    └──requires──> [Target Tracking] (smooths track position stream)
    └──enhances──> [Mini-map Display]

[Human Confirmation UI]
    └──requires──> [Escalation State Machine] (nothing to confirm without escalation)
    └──feeds──> [Audit Log]
```

### Dependency Notes

- **Acoustic Detection → Vision Confirmation:** Vision is only triggered by an acoustic event crossing `ACOUSTIC_TRIGGER_THRESHOLD`. Vision does not run continuously.
- **Vision Confirmation → Sensor Fusion:** Fusion can proceed without vision (acoustic-only track) but threat level is capped at CAUTION until vision confirms.
- **Sensor Fusion → Escalation State Machine:** Threat level transitions are gated on fused confidence crossing configurable thresholds.
- **Escalation State Machine → Target Tracking:** Track initiation fires on ALERT or above — only after positive fusion confirmation (mirrors the positive-ID rule in fielded systems).
- **Kalman Filter requires Target Tracking:** Cannot smooth a track that doesn't exist; must be built after basic tracking is working.
- **Bounding-box Thumbnail requires Vision Result payload:** CV model response must include box coordinates; this must be specified in the Vision API contract before the app UI is built.

---

## MVP Definition

### Launch With (Demo v1 — Full Fused Alert Flow)

The goal is one convincing end-to-end run from acoustic event to human-confirmed threat.

- [ ] Simulated acoustic detection with confidence score + WebSocket event emission
- [ ] Acoustic event triggers vision pipeline (simulated POV + hosted CV model)
- [ ] Vision result with confidence + (optional) bounding box returned as event
- [ ] Late fusion: weighted acoustic + visual → fused confidence → threat level enum
- [ ] 4-level escalation state machine driven by fusion events
- [ ] Escalating recommendation cards in the C2 app with human confirm / stand-down
- [ ] Agent reasoning trail connected to live events (not scripted)
- [ ] Live threat level + sensor status display in the C2 app
- [ ] Simulated target tracking with basic position updates + mini-map dot
- [ ] Audit log of operator confirmations

### Add After Core Flow is Validated (v1.x)

- [ ] Bounding-box frame thumbnail in reasoning trail — adds visual "proof"
- [ ] Kalman filter on track position + uncertainty ellipse on mini-map
- [ ] Acoustic-only fallback track when vision times out
- [ ] Drone model/type classification (multi-class acoustic output)
- [ ] Sensor degradation banners ("VISION ONLY", "ACOUSTIC ONLY")

### Future / Post-Hackathon (v2+)

- [ ] Cascaded acoustic make → model classification
- [ ] Real Raspberry Pi microphone adapter swap-in
- [ ] Real Meta Glasses POV feed adapter swap-in
- [ ] Multi-target tracking
- [ ] RF / radar fusion layer
- [ ] Secondary confirmation request workflow
- [ ] ROE zone visualization
- [ ] Event replay / mission replay mode

---

## Feature Prioritization Matrix

| Feature | Demo Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Acoustic detection + WebSocket event | HIGH | LOW | P1 |
| Vision pipeline trigger + CV model call | HIGH | LOW | P1 |
| Late fusion → threat level | HIGH | LOW | P1 |
| Escalation state machine + recommendations | HIGH | LOW | P1 |
| Human confirm / stand-down UI | HIGH | LOW | P1 |
| Agent reasoning trail (live) | HIGH | LOW | P1 |
| Simulated target tracking + mini-map dot | HIGH | LOW | P1 |
| Sensor status indicators | HIGH | LOW | P1 |
| Bounding-box frame thumbnail | HIGH | MEDIUM | P2 |
| Kalman filter + uncertainty ellipse | MEDIUM | MEDIUM | P2 |
| Confidence meter per sensor | MEDIUM | LOW | P2 |
| Acoustic-only fallback handling | MEDIUM | LOW | P2 |
| Drone model classification | MEDIUM | MEDIUM | P2 |
| Sensor degradation banners | MEDIUM | LOW | P2 |
| Countermeasure option cards (display only) | MEDIUM | LOW | P2 |
| ROE zone overlay on mini-map | MEDIUM | MEDIUM | P3 |
| Secondary confirmation request | LOW | MEDIUM | P3 |
| Event replay / history | LOW | MEDIUM | P3 |
| Live video streaming in app | LOW | HIGH | Anti-feature |
| Autonomous countermeasure execution | NEGATIVE | HIGH | Anti-feature |

**Priority key:**
- P1: Must have for launch — the demo doesn't work without these
- P2: Should have — significantly improves demo credibility / visual impact
- P3: Nice to have — adds polish; defer if time is tight
- Anti-feature: Explicitly skip

---

## Competitor Feature Reference

| Feature | Dedrone / DedroneTracker.AI | HENSOLDT Elysion | TrackDeep C2 | Sentry-CD Approach |
|---------|----------------------------|------------------|--------------|-------------------|
| Multi-sensor fusion | RF + radar + acoustic + optical | Same | Same | Acoustic + vision (simulated); architecture is sensor-agnostic |
| Threat classification | AI/ML multi-sensor | AI-assisted | AI-assisted | Late fusion weighted average; hosted pretrained CV |
| Escalation / kill chain | Automated with human override | Automated priority with countermeasure proposal | Automated alerts + human auth | Human-gated at every level; recommendations only |
| Operator interface | Web dashboard, map-based | Map + video + panel | Web dashboard + visual overlays | Mobile (Expo RN); mini-map + orb + reasoning trail |
| Mission replay | Yes | Yes | Yes | Event log; replay is P3 |
| Autonomous countermeasure | Jammer / GNSS integration | Effector control | Platform recommends; human authorizes | Never autonomous — recommendations only |
| Acoustic-only detection | Yes (acoustic contributes to fusion) | Yes | Yes | Yes (acoustic-only fallback track at CAUTION) |

---

## Sources

- Dedrone DedroneTracker.AI whitepaper — https://www.dedrone.com/white-papers/counter-uas (MEDIUM confidence — vendor marketing + technical description)
- HENSOLDT Elysion C-UAS Mission Core — https://www.hensoldt.net/products/elysion-mission-core-best-in-class-counter-uas-software (HIGH — product datasheet)
- TrackDeep C2 Platform — https://trackdeep.ai/c2/ (HIGH — product datasheet)
- MidRadar Integrated Counter-UAV — https://midradar.com/integrated-counter-uav/ (HIGH — human-confirmation and audit log details)
- MAG Aerospace Counter-UAS technologies — https://www.magaero.com/mag-thought-leadership-strategic-counter-uas-defense-technologies-and-mitigation-strategies/ (MEDIUM — industry overview)
- QuickSet: How Counter-UAS Systems Work — https://www.quickset.com/how-counter-uas-systems-work/ (HIGH — slew-to-cue, false positive, EO/IR confirmation details)
- Drone Warfare: EO/IR Detection — https://drone-warfare.com/counter-uas/eo-ir-detection/ (MEDIUM — technical overview)
- SAAB 9LV CUAS CMS — https://www.saab.com/globalassets/markets/australia/ip-23/20231030-auscms-cuas_final.pdf (HIGH — escalation, ROE, kill chain patterns)
- hilariie/Counter-UAS (GitHub) — https://github.com/hilariie/Counter-UAS (HIGH — simulated C-UAS architecture directly comparable to this project)
- AALIS acoustic classifier (GitHub) — https://github.com/IAMAMZ/aalice-drone-detection-knn-backend (HIGH — acoustic feature + SNR threshold implementation reference)
- AUDRON: Audio-based Drone Recognition Network — https://arxiv.org/pdf/2512.20407 (HIGH — MFCC+STFT+RNN+Autoencoder; 98.51% accuracy)
- DronePrint: Acoustic Signatures — https://www.youtube.com/watch?v=8rhi3LqFYl4 (MEDIUM — cascaded make/model classification reference)
- Counter UAV Radar: Centralized Command Platform Design — https://www.counteruavradar.com/en/knowledge-base/centralized-command-platform-design/ (HIGH — C2 dashboard design patterns, alert categorization, sensor health)
- Grayhill: Human-in-the-Loop HMI for AI-Enabled Defense — https://grayhill.com/blog/human-in-the-loop-hmi-for-ai-enabled-defense-systems/ (HIGH — HITL design principles)
- Royal Military Academy: Human Factors in C-UAS HMI Design — https://researchportal.rma.ac.be/en/publications/human-factors-in-the-design-of-humanmachine-interfaces-for-counte/ (HIGH — uncertainty display, evidence bundles, HMI performance indicators)
- MDPI: Ensemble learning for micro-drone acoustic detection — https://link.springer.com/article/10.1007/s44163-026-00869-1 (HIGH — false positive rates, ensemble methods)
- DIDIT (Telespazio) — https://www.telespazio.de/en/products/didit (HIGH — automated visual verification, AI classification workflow)

---

*Feature research for: Sentry-CD body-worn acoustic + vision counter-drone C2 (simulated demo)*
*Researched: 2026-06-14*
