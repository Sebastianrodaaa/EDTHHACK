# Domain Pitfalls

**Domain:** Body-worn acoustic + vision counter-drone (counter-UAS) early-warning C2 — simulated end-to-end demo
**Project:** Sentry-CD
**Researched:** 2026-06-14
**Confidence:** HIGH (acoustic/CV/WebSocket pitfalls from multiple technical sources); MEDIUM (HITL/ethics framing, demo-specific)

---

## Critical Pitfalls

Mistakes that cause rewrites, demo failures, or irretrievably broken threat scoring.

---

### Pitfall 1: Acoustic False Positive Cascade — Spectral Overlaps Not Handled

**What goes wrong:** The acoustic detector triggers on birds, helicopters, motorcycles, HVAC fans, or wind — objects whose propeller/wing harmonics and broadband noise overlap with drone rotor signatures (200–8000 Hz). In a simulated demo the `DroneSimulator` produces clean spectrograms; the pipeline looks perfect. At the actual demo venue (crowd noise, HVAC, someone outside with a petrol scooter) the simulated detector fires continuously or not at all, undermining the narrative.

**Why it happens:** Developers hard-code a single MFCC feature threshold during indoor development. The threshold is calibrated to their laptop fan noise floor, not the demo room. CNN-based systems report <2% false positive rate in controlled lab conditions but operational rates "typically exceed test conditions due to environmental complexity" (drone-warfare.com).

**Consequences:**
- Continuous false-alarm rain → confidence scores are permanently high → the "escalation" story collapses
- Zero detections under real noise → nothing to demo
- Fusion layer misinterprets spurious acoustic events as high-confidence pre-triggers, causing the CV pipeline to start unnecessarily

**Prevention:**
- Build a **playback harness** with pre-recorded representative clips (birds, city ambience, indoor crowd) and run the acoustic classifier against each before freezing thresholds
- Add a **minimum-duration gate**: require the drone signature to persist ≥ 300 ms before raising an event (removes impulse noise)
- Log all raw detection probabilities during rehearsal; tune the threshold to maintain < 1 false positive per 60-second window
- For demo: use the **simulated acoustic adapter** with a scripted event schedule — remove dependency on live microphone capture for the scored portions

**Warning signs:** Classifier fires > 3 times per minute during a quiet rehearsal room; simulated mode shows a different confidence trajectory than "live" mode.

**Phase:** Acoustic Detection Phase / Demo Hardening Phase

---

### Pitfall 2: Fusion Confidence Miscalibration — Raw Scores Not Comparable Across Modalities

**What goes wrong:** The acoustic model outputs a probability of 0.82 and the CV model outputs a confidence of 0.79 — both look like "80% confident" but they are not comparable numbers. They come from different loss functions, class distributions, and non-maximum suppression settings. Naively averaging or multiplying them produces a fused score that is **systematically overconfident or systematically underconfident** depending on which model dominates.

**Why it happens:** "A score of 0.8 from a camera detector does not necessarily correspond to the same empirical correctness rate as a score of 0.8 from a LiDAR detector. Miscomparability arises from differences in training losses, class imbalance, non-maximum suppression behavior, and sensor-specific failure patterns." (JTIE uncertainty-aware late fusion paper, 2024). Neural networks in general tend to output overconfident predictions; fusing two overconfident sources compounds the problem.

**Consequences:**
- Threat level shows 87% even when only the acoustic arm fires — visually compelling but technically misleading
- Operators / judges see confidence numbers that bounce erratically (90% → 40% → 95%) when one modality drops out
- Confidence bar in the mobile C2 becomes meaningless as a trust signal

**Prevention:**
- Apply **per-modality calibration** before fusion: at minimum use temperature scaling (divide logit by learned temperature T) to map raw outputs to calibrated probabilities
- In simulation: **pre-define the calibration mapping** using a small hand-crafted lookup table (e.g., acoustic score 0.8 → calibrated 0.65 based on known model precision), document the reasoning in code comments
- Use **Dempster-Shafer evidence theory** or a simple weighted sum with explicit modality weights rather than raw product fusion; make weights visible in code
- Validate the fused confidence against a small test scenario matrix (acoustic only, CV only, both, neither) and assert expected ranges before committing to the fusion formula
- Display confidence with **explicit modality breakdown** in the C2 (e.g., "A:0.65 V:0.71 → Fused:0.68") so judges can see the logic, not just the number

**Warning signs:** Fused score jumps > 30 percentage points when one modality flips between detections; score stays high after the CV model returns "no drone".

**Phase:** Fusion / Late Fusion Phase

---

### Pitfall 3: Sound ↔ Vision Timing Mismatch — Events Arrive Out of Causal Order

**What goes wrong:** The acoustic detection fires at T=0. The system dispatches a request to the CV pipeline. The CV result arrives at T=1.8 s (network round-trip + inference). The fusion engine receives vision BEFORE it has properly marked the acoustic trigger window, or the UI shows "vision confirmed" before the "acoustic alert" label has rendered. To a judge watching the mobile screen, the causal sequence looks reversed or simultaneous rather than "sound → trigger → vision → confirm."

**Why it happens:** WebSocket messages are not guaranteed to arrive in wall-clock order when sent from separate async tasks. Each pipeline stage publishes events independently; the mobile client receives them in TCP delivery order, which may differ from emission order when back-pressure causes queuing.

**Consequences:**
- The demo narrative ("sound finds it, camera confirms it") is broken visually
- Late fusion score is computed before all inputs are assembled → stale partial score displayed
- "Escalation ladder" fires a step early because the first partial score crosses a threshold

**Prevention:**
- Attach a **monotonic sequence number** and a **causal parent ID** to every event (`acoustic_event_id` is echoed in the vision result and in the fusion event)
- The fusion engine **holds a short buffer** (configurable, default 2 s): it waits for either the vision result or a timeout before emitting the fused score
- The mobile C2 renders events in **sequence-number order** regardless of WebSocket arrival order (simple priority queue keyed on seq)
- Add a `triggered_by` field to the vision request so the C2 can draw the → arrow in the reasoning trail correctly even if events arrive reordered
- In the simulated scenario, **serialize the event emissions** with explicit `asyncio.sleep` delays (0 ms, 200 ms, 1 800 ms) to reproduce realistic timing without real hardware

**Warning signs:** The reasoning trail in the C2 shows "Vision Confirmed" above "Acoustic Alert"; fusion score changes twice in rapid succession.

**Phase:** Backend Pipeline Phase / WebSocket Integration Phase

---

### Pitfall 4: WebSocket Disconnect Silently Drops Events During Demo

**What goes wrong:** A mobile client on WiFi reconnects after a brief lapse (phone screen lock, roaming between access points). The FastAPI server has no replay buffer. Events emitted during the disconnect are lost forever. The C2 displays a frozen state while the backend has already escalated. Judges see "MONITOR" on the phone while the server log shows "ALERT SQUAD."

**Why it happens:** FastAPI's WebSocket primitives give you raw connections, not a messaging system. "There are no rooms, no presence, no message history. You build those yourself." (websocket.org). The common tutorial pattern — `manager.broadcast(message)` — silently discards messages to disconnected clients.

**Consequences:**
- Mobile C2 misses escalation transitions; threat state is stale
- On reconnect, the client has no way to recover current state — it shows "MONITOR" indefinitely
- Demo appears broken even though the backend is correct

**Prevention:**
- Implement a **last-N event ring buffer** (e.g., 20 events) in the connection manager; send the full buffer as a `state_sync` message immediately on reconnect
- Add a **state snapshot endpoint** (`GET /state/current`) that the mobile client polls on reconnect as a fallback
- Send **heartbeat pings every 5 s** from the server; the client restarts the connection if it misses 2 consecutive pings
- Use **`asyncio.shield`** or catch send errors per-client to prevent one slow/disconnected client from blocking broadcasts to others
- For demo: run both backend and client on the same LAN with a **dedicated hotspot** (not conference WiFi) to eliminate most disconnect triggers

**Warning signs:** `WebSocketDisconnect` exceptions in server logs not followed by a reconnect confirmation; C2 state frozen for > 10 s while backend logs show activity.

**Phase:** WebSocket / Backend Phase

---

### Pitfall 5: Hosted CV API Latency and Rate-Limit Surprises Under Demo Conditions

**What goes wrong:** During development the CV API responds in 300 ms. On demo day, the conference network adds 800 ms of latency. After 20 test runs the API starts returning 429 (rate limit) or the free tier quota is exhausted. The first time a judge watches, the CV confirmation never arrives and the threat stays at acoustic-only confidence.

**Why it happens:** Free-tier hosted inference APIs (Roboflow serverless, HuggingFace Inference API, Replicate) impose daily request quotas (often 1 000–10 000/day) and enforce rate limits (often 10–60 req/min). Development testing burns quota. Conference internet adds 300–900 ms variable latency. "A result 500 ms late is worthless" for a hard real-time pipeline (getstream.io).

**Consequences:**
- CV arm returns timeout → fusion falls back to acoustic-only → confidence never reaches the "ALERT" threshold → demo stalls
- Rate limit hit mid-demo → entire vision pipeline silently fails
- Latency variance makes the confidence bar animate erratically rather than the smooth staged reveal the demo requires

**Prevention:**
- **Cache the top 5 demo-scenario image responses** locally; implement a `CV_MOCK_MODE` flag that returns the cached response with a realistic 400–800 ms simulated delay instead of calling the API
- **Instrument quota usage** during development: log every API call; stop automated testing at 80% of daily quota
- Choose an API with **adequate free throughput** for the demo (Roboflow serverless: 1 000 images/month on free; consider upgrading or using the Docker container locally)
- Set a **CV timeout of 3 s** with a graceful degradation path: if vision times out, emit a `vision_timeout` event and proceed with acoustic-only fusion at reduced confidence — never hang the pipeline
- For maximum reliability: run inference locally in a Docker container (`roboflow/inference`) on the demo laptop — eliminates network dependency entirely

**Warning signs:** API response times > 1 s during rehearsal on the venue network; quota dashboard shows > 60% consumed before demo day.

**Phase:** CV Integration Phase / Demo Hardening Phase

---

### Pitfall 6: Demo Scenario Is Not Scripted and Repeatable

**What goes wrong:** The demo uses a "live" simulation that generates random detection timing. Each rehearsal run produces a different sequence of events, different confidence values, different escalation timing. On demo day the sequence that worked perfectly in rehearsal doesn't occur. The presenter fumbles because the phone screen shows something unexpected.

**Why it happens:** Developers optimise for technical correctness (stochastic realistic behaviour) rather than demo reliability (deterministic narrative). The two goals are in direct conflict.

**Consequences:**
- The confidence bar reaches "ALERT" in 8 s during rehearsal but takes 45 s on demo day — the presenter is forced to ad-lib for 37 s
- An escalation step is skipped because random timing collapsed two events together
- The reasoning trail shows steps out of order, undermining the "AI agent logic" narrative

**Prevention:**
- Implement a **scripted scenario mode**: a YAML/JSON file defines the exact event sequence with millisecond-resolution offsets (`t=0: acoustic_detect confidence=0.71`, `t=1800: vision_confirm confidence=0.79`, etc.)
- The simulated pipeline reads from this script in demo mode; the random simulator is only used for development/testing
- Number every scenario (`scenario_01_basic_drone.yaml`, `scenario_02_false_alarm_bird.yaml`) and rehearse each one separately
- Add a **"reset"** button in the C2 that sends a `RESET_SCENARIO` command to the backend, replaying the script from T=0 — allows judges to request a second demonstration without restarting services
- **Freeze the demo script 2 hours before presentation**; no code changes after that point

**Warning signs:** Each rehearsal run shows different confidence values or escalation timing; presenter has to narrate "it should do X now" while watching the screen.

**Phase:** Demo Integration Phase (entire milestone)

---

## Moderate Pitfalls

---

### Pitfall 7: Automation Bias / Alert Fatigue in Human-in-the-Loop UX

**What goes wrong:** The escalation ladder fires too many intermediate steps (MONITOR → SECONDARY_CONFIRM → ALERT_SQUAD → PREPARE_COUNTERMEASURES) in quick succession during development. Operators (and judges watching) learn to rubber-stamp every confirmation button. The system appears to be making the decision; the human is just clicking "OK." This undermines the "human always in control" safety narrative — exactly the wrong impression for a counter-drone demo where ethics framing matters.

**Why it happens:** "The more automation is added to a system, and the more reliable and robust that automation is, the less likely that human operators will be aware of critical information and able to take over manual control when needed." (UNIDIR Human-Machine Interfaces, 2022). Rapid escalation with no evidence display trains operators to click through.

**Prevention:**
- Each escalation step must display the **evidence that triggered it**: acoustic spectrogram thumbnail, CV bounding-box frame, fused confidence breakdown — not just a confidence number
- Add a **minimum dwell time** per escalation step (e.g., 5 s before the "Confirm" button becomes active) to force the operator to read the evidence
- Design the CONFIRM button as deliberate, not reflexive: large, labelled with the consequence ("ALERT SQUAD — this notifies all team members")
- Keep escalation levels to **3 meaningful stages** maximum for a demo: MONITOR → ALERT → COUNTERMEASURE_OPTIONS
- Never auto-advance escalation levels — human click required at each transition

**Warning signs:** Judges or teammates skip reading the evidence and click Confirm immediately; escalation completes in < 15 s total.

**Phase:** Mobile C2 / UX Phase

---

### Pitfall 8: False Negative Trap — Silent Miss During "Threat Present" Phase

**What goes wrong:** The acoustic detector misses a drone event because background noise pushes SNR below threshold. No event fires. The UI stays green. The demo scenario is "threat present and escalating" but the phone shows "ALL CLEAR." The presenter is forced to explain why the system did nothing.

**Why it happens:** A single fixed detection threshold cannot be optimal for all noise environments. Low threshold → many false positives (Pitfall 1). High threshold → misses in noisy venues.

**Prevention:**
- Use **adaptive thresholding**: compare against a rolling 30-second baseline noise floor rather than a fixed absolute threshold
- In simulated mode: use the scripted event schedule (Pitfall 6 mitigation) which always fires exactly when the script says, regardless of background noise
- Define a **"health check" event** that fires every 30 s confirming the acoustic node is alive and listening — if it goes silent, the C2 shows "SENSOR OFFLINE" rather than "ALL CLEAR"

**Warning signs:** Entire rehearsal runs produce zero detections; the confidence bar never moves.

**Phase:** Acoustic Detection Phase

---

### Pitfall 9: "Human-in-the-Loop" as Hollow Ethics Claim

**What goes wrong:** The demo script and slide deck claim "human always in the loop" as a safety feature, but the UI shows an autonomous threat level escalating to the highest tier with a single enabled "Acknowledge" button. Judges who understand defense AI policy will notice the difference between "a human can acknowledge" and "a human exercises meaningful control with sufficient situational awareness, time, and information to make a decision."

**Why it happens:** "Human in the loop" is frequently used as a checkbox claim rather than an architectural property. The DoD DODI 3000.09 and UNIDIR literature distinguish between the human's *role*, *timing*, and *authority*. A demo that shows autonomous escalation with a rubber-stamp confirm button is architecturally "human on the loop" (supervisory) not "human in the loop" (decision-making).

**Consequences:**
- Credibility damage with technically literate judges
- Misrepresents the safety story of the product concept

**Prevention:**
- Frame the system explicitly as **"human-on-the-loop"** (supervisory) rather than "human-in-the-loop" (interruptive) — this is accurate and defensible
- Ensure the C2 UI shows the **operator's decision consequence** at each escalation step ("Alerting squad will notify 6 people")
- Include a **DISMISS / FALSE ALARM** button at every escalation step that is as prominent as CONFIRM — this is the meaningful control action
- In the demo narrative, walk through a false-alarm scenario (Pitfall 1 sibling) where the operator correctly dismisses — this is more impressive than showing the happy path only

**Warning signs:** The DISMISS button is missing or styled in grey; the narrative never shows an operator overriding the system.

**Phase:** Mobile C2 / Ethics Framing Phase

---

### Pitfall 10: FastAPI Sync-in-Async Blocking — Event Loop Stall During Demo

**What goes wrong:** A synchronous operation (file I/O for logging, a blocking `time.sleep` in a simulated sensor, a CPU-bound feature extraction loop) runs directly inside an `async def` route or WebSocket handler. This blocks the entire `uvicorn` event loop. All connected clients freeze — the mobile app stops receiving events — for the duration of the blocking call.

**Why it happens:** Python's `asyncio` is cooperative; a synchronous call inside `async def` starves all other coroutines. "The `task.cancel()` in the except block is critical. Without it, the background task keeps running after the client disconnects." (websocket.org FastAPI guide). Beginners add `time.sleep()` to simulate sensor latency without realising the impact.

**Prevention:**
- Replace all `time.sleep()` calls with `await asyncio.sleep()`
- Run CPU-bound processing (feature extraction, MFCC, any numpy-heavy transform) in a `ProcessPoolExecutor` via `loop.run_in_executor`
- All file I/O (logging, scenario script reading) must use `aiofiles` or be offloaded to an executor
- During development, run `uvicorn` with `--workers 1` and add a debug middleware that logs event-loop block durations > 50 ms

**Warning signs:** Mobile app freezes for several seconds then receives a burst of events; server CPU spikes to 100% during feature extraction while WS messages queue up.

**Phase:** Backend / WebSocket Phase

---

## Minor Pitfalls

---

### Pitfall 11: Mobile Reconnect Loop Kills WiFi During Demo

**What goes wrong:** The Expo/RN WebSocket client has an aggressive reconnect loop (e.g., retry every 200 ms). During a brief network hiccup it spawns dozens of simultaneous TCP connections to the FastAPI server before the server's OS file-descriptor limit is hit, or floods the conference WiFi with SYN packets.

**Prevention:**
- Implement **exponential backoff** with jitter in the WS client: base=500 ms, max=30 s
- Cap max concurrent pending reconnect attempts to 1 (cancel the previous attempt before scheduling the next)
- On the server, reject connections that arrive faster than 1/s from the same IP with a 5-second cooldown

**Phase:** WebSocket / Mobile Integration Phase

---

### Pitfall 12: Confidence Score UI Showing Raw Float Precision

**What goes wrong:** The confidence bar displays "0.6723048..." or "73.14159%". Judges read precision as accuracy. Displaying 6 decimal places implies the system knows the threat is 67.23% likely when the underlying fusion formula has no such resolution.

**Prevention:**
- Round displayed confidence to **1 decimal place** (e.g., "67.2%") or bin into labelled ranges (LOW / MEDIUM / HIGH / CRITICAL)
- Accompany every confidence display with a **plain-language description**: "Possible drone — acoustic match, no visual yet"
- Never display internal floating point directly; pass through a `format_confidence(score: float) -> str` utility

**Phase:** Mobile C2 / UX Phase

---

### Pitfall 13: Expo Dev Build Crashing Under Demo Pressure

**What goes wrong:** The Expo iOS dev build works perfectly during development but crashes or shows a yellow box error during the demo when the WebSocket receives an unexpected event shape.

**Prevention:**
- Add **Zod (or manual) runtime validation** on every incoming WebSocket message in the RN client; reject and log malformed events rather than crashing
- Test the client against a malformed/missing-field payload before the demo
- Use `ErrorBoundary` wrappers around the threat display and reasoning trail components so a crash in one component doesn't kill the entire screen

**Phase:** Mobile C2 / Integration Phase

---

### Pitfall 14: Hosted CV API Key in Source Code

**What goes wrong:** The Roboflow / HuggingFace API key is hardcoded in `backend/cv_client.py`. It gets pushed to the hackathon GitHub repo (which is public for judging). The key is immediately harvested by credential-scanning bots.

**Prevention:**
- Store all keys in `.env` (ensure `.env` is in `.gitignore` from day one)
- For the demo machine: use environment variables injected at runtime
- If the key does get pushed: revoke it immediately, generate a new one, and add a pre-commit hook

**Phase:** CV Integration Phase (Day 1)

---

## Phase-Specific Warning Map

| Phase / Topic | Highest-Risk Pitfall | Mitigation Priority |
|---|---|---|
| Acoustic detection (simulated) | Pitfall 1 (false positive cascade) | HIGH — calibrate threshold against venue noise before freezing |
| Fusion / confidence scoring | Pitfall 2 (miscalibrated scores) | CRITICAL — define calibration formula before writing UI |
| Backend event pipeline | Pitfall 3 (timing disorder) | HIGH — add sequence numbers and causal IDs on day 1 |
| WebSocket backbone | Pitfall 4 (disconnect / event loss) | HIGH — implement ring buffer and state-sync on reconnect |
| CV integration | Pitfall 5 (latency / rate limits) | HIGH — build CV mock mode before integrating real API |
| Demo scripting | Pitfall 6 (non-repeatable flow) | CRITICAL — scripted scenario mode required before any rehearsal |
| Mobile C2 UX | Pitfall 7 (automation bias) | MEDIUM — add evidence display and dwell time to confirm |
| Mobile C2 UX | Pitfall 9 (hollow HITL claim) | HIGH — include DISMISS button; use correct framing in narrative |
| FastAPI backend | Pitfall 10 (sync-in-async stall) | HIGH — audit all async handlers for blocking calls |
| Mobile C2 integration | Pitfall 12 (float precision in UI) | LOW — 1-line fix; do it early to establish good habits |
| Mobile C2 reliability | Pitfall 13 (Expo crash on bad event) | MEDIUM — add runtime validation + ErrorBoundary |
| Security | Pitfall 14 (API key in source) | HIGH — `.env` + `.gitignore` on day 1 |

---

## Sources

- Counter-UAS 101 – Acoustic Drone Detection. drone-warfare.com (MEDIUM confidence — industry source, no peer review; corroborated by PMC review below)
- Advances and Challenges in Drone Detection and Classification Techniques: A State-of-the-Art Review. PMC / NCBI 2024. pmc.ncbi.nlm.nih.gov/articles/PMC10780901/ (HIGH confidence — peer-reviewed survey)
- D-Fend Solutions: The False Positive Dilemma. d-fendsolutions.com (MEDIUM confidence — vendor whitepaper, qualitative)
- Uncertainty-Aware Late Fusion for 3D Perception. JTIE 2024. jtie.stekom.ac.id (MEDIUM confidence — recent paper, applied setting)
- BachelorThesis Malte Rost: Probabilistic Late Fusion (Bayesian), OvGU (MEDIUM confidence — thesis, well-documented)
- FastAPI WebSocket Guide. websocket.org (HIGH confidence — official ecosystem documentation)
- Weaponizing Real Time: WebSocket/SSE with FastAPI. blog.greeden.me 2025 (MEDIUM confidence — practitioner post, corroborated by FastAPI docs)
- Best Practices for Building Low-Latency Vision AI Pipelines. getstream.io (MEDIUM confidence — practitioner post)
- Roboflow Inference / Model Deployment documentation. blog.roboflow.com (HIGH confidence — official documentation)
- Low-Latency Autonomous Surveillance (MDPI Computers 2025). mdpi.com/2073-431X/15/1/62 (HIGH confidence — peer-reviewed, defense domain)
- Human-in-the-Loop AI Security: The 2026 Oversight Framework. intellisee.com (MEDIUM confidence — industry analyst)
- UNIDIR Human–Machine Interfaces in Autonomous Weapon Systems. unidir.org 2022 (HIGH confidence — UN Institute for Disarmament Research)
- How to Build a Demo in 72 Hours. medium.com/@sinceai (MEDIUM confidence — practitioner, widely cited in hackathon communities)
- Build Demo Infrastructure First. marioottmann.com 2024 (MEDIUM confidence — practitioner)
