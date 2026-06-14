# Sentry-CD Backend

FastAPI + WebSocket gateway for the body-worn acoustic-vision counter-drone
sentry. Runs the full simulated pipeline in one process:

```
ScenarioEngine → AcousticAdapter → AcousticNode → VisionWorker → FusionEngine
              → Tracker → EventBus → WebSocket Gateway → Mobile C2
```

Every hardware input sits behind an adapter seam (`adapters/`), so the simulated
acoustic mic and POV vision can be swapped for a Raspberry Pi mic array and a
hosted CV model with no changes to the processing or gateway layers.

## Setup

```bash
cd backend
uv venv --python 3.11 .venv
uv pip install -r requirements.txt --python .venv
```

## Run

```bash
.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

- `0.0.0.0` so a physical device on the LAN can reach it. For the iOS simulator,
  `localhost` works from the app.
- The mobile app connects to `ws://<host>:8000/ws`. Set
  `EXPO_PUBLIC_SERVER_HOST=<lan-ip>` before `expo start` for a real device.

## Demo runbook

1. Start the backend (above). Confirm `GET /health` returns `{"status":"ok"}`.
2. Launch the app (`npm run ios`). Header should show **Live**.
3. Tap **Run scenario** (or `POST /scenario/demo-alpha/start`):
   - acoustic frames stream; orb turns **red** on the early acoustic warning;
   - reasoning trail advances (acquisition → spectral → POV vision → assessment);
   - vision confirms a drone → fused **HIGH/CRITICAL** assessment;
   - ThreatPanel shows fused/acoustic/vision confidence + an escalating
     recommendation (alert squad / prepare countermeasures);
   - the tracking compass opens and the range closes.
4. Operator taps **Confirm** (logged to `/audit`), **Escalate**, or **Stand down**
   (clears the threat, orb back to white).
5. **False alarm:** `POST /scenario/demo-bravo/start` — vision classifies a bird,
   fusion downweights it, threat stays **LOW**, recommendation is *monitor*, and
   no track opens. Demonstrates restraint / human-in-the-loop.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/health` | liveness + client count |
| GET  | `/state` | current state snapshot |
| GET  | `/scenarios` | list available scenarios |
| POST | `/scenario/{id}/start` | start a scenario |
| POST | `/scenario/stop` | stop the active scenario |
| POST | `/scenario/reset` | stop + clear threat state |
| POST | `/operator/action` | operator HITL action (confirm/escalate/stand_down/acknowledge) |
| GET  | `/audit` | operator action audit log |
| WS   | `/ws` | live event stream (snapshot on connect, replay on reconnect) |

## Configuration (env vars)

`ACOUSTIC_ADAPTER`, `VISION_ADAPTER`, `CV_MOCK_MODE` (`scripted`|`random`),
`VISION_LATENCY_S`, `VISION_TIMEOUT_S`, `ACOUSTIC_CONF_THRESHOLD`,
`ACOUSTIC_GATE_FRAMES`, `FUSION_WEIGHT_ACOUSTIC`, `FUSION_WEIGHT_VISION`,
`ACOUSTIC_ONLY_CONF_CAP`, `EVENT_BUFFER_SIZE`. See `config.py`.

## Tests

In-process (no server needed):

```bash
.venv/bin/python tests/smoke_phase1.py   # gateway + acoustic sim + replay
.venv/bin/python tests/smoke_phase2.py   # acoustic → vision trigger
.venv/bin/python tests/smoke_phase3.py   # fusion + escalation + audit
.venv/bin/python tests/smoke_phase5.py   # tracking + false-alarm restraint
```

Live network (server must be running):

```bash
.venv/bin/python tests/live_client.py    # real ws:// transport contract
```
