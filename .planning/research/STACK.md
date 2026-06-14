# Stack Research

**Domain:** Counter-drone acoustic + vision C2 system (simulated demo)
**Researched:** 2026-06-14
**Confidence:** HIGH (versions verified against PyPI, official docs, and Roboflow pricing pages)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | ≥3.11 | Runtime for all backend services | 3.11 asyncio performance; required by ultralytics 8.4.x dev tooling; broad library support |
| FastAPI | 0.136.3 | HTTP + WebSocket event backbone | Current PyPI latest (Jun 2026); Pydantic v2 native; WebSocket via Starlette; zero-friction async |
| uvicorn[standard] | ≥0.34 | ASGI server | Ships with uvloop for high-throughput async; required by FastAPI |
| Pydantic | v2.9+ | Event schema validation | Required by FastAPI 0.115+; v1 support fully dropped; `model_validate`, `model_dump` are the canonical API |
| librosa | 0.11.0 | Acoustic DSP — MFCC, mel spectrogram, onset detection | Latest stable (Mar 2025); SciPy FFT backend by default; standard in all recent UAV acoustic research (arXiv 2505.23782, ASTESJ 2024); direct `stft`, `feature.mfcc`, `feature.melspectrogram` APIs |
| numpy | ≥2.0 | Array operations, synthetic audio generation | librosa 0.11.0 explicitly supports NumPy 2.0; needed for vectorised signal synthesis |
| scipy | ≥1.15 | Signal processing, bandpass filtering | librosa 0.11.0 switched default FFT backend to scipy; use `scipy.signal.butter` + `sosfilt` for frequency band isolation |
| ultralytics | 8.4.61 | Local YOLO11 drone vision inference | Latest PyPI (Jun 2026); loads pre-trained HF Hub drone model in one line; offline-capable; zero API cost; AGPL-3.0 |
| sounddevice | 0.5.5 | Optional real-mic audio input | Latest PyPI; NumPy-native InputStream; cleanest PortAudio binding for Python; used when swapping from simulated to real RPi mic |

### Vision Model — Hosted/Pre-trained Options

> **For the simulated demo, run ultralytics locally**. The hosted Roboflow API is the correct swap-in when you want to delegate inference to the cloud.

| Option | Model | Latency | Cost | Notes |
|--------|-------|---------|------|-------|
| **Local (primary)** | `sapoepsilon/yolov11s-drone-detector` via ultralytics | <100ms on CPU | Free | 92.9% precision, 19MB, Apache 2.0; loads from HF Hub: `YOLO("sapoepsilon/yolov11s-drone-detector")` |
| **Local (multi-class)** | `TomSmail/drone-yolo-v1` via ultralytics | <100ms on CPU | Free | Distinguishes quadcopter vs fixed-wing Shahed-type; includes monocular distance estimate |
| **Hosted (fallback)** | Roboflow `yolodrone/drone-object-detection-v2` | 185–350ms (US) | ~$0.45/h @ 1 req/10s | Use `inference` SDK; $4/credit; ~0.2 credits/1000 warm inferences; cold start adds 500–3000ms |

### FastAPI WebSocket Backbone Pattern

Single-process LAN demo — no Redis, no multi-worker needed.

```python
# Pattern: ConnectionManager + asyncio producer task
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, payload: dict):
        dead = []
        for conn in self.active:
            try:
                await conn.send_json(payload)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.active.remove(conn)
```

Use `asyncio.create_task` to push events from the simulation engine into the ConnectionManager without blocking the receive loop. Sensor events go in, JSON envelope comes out: `{type, ts, payload, confidence}`.

### React Native WebSocket Client

| Component | Choice | Notes |
|-----------|--------|-------|
| WS transport | Native `WebSocket` (RN built-in) | Sufficient for LAN; no extra install |
| Auto-reconnect | `reconnecting-websocket` 4.4.0 | Drop-in API-compatible wrapper; exponential backoff; works in RN |
| State wiring | Existing zustand store | Add a `ws` slice that dispatches incoming events; keep RN app changes minimal |

```typescript
// In zustand store — add this slice
import ReconnectingWebSocket from 'reconnecting-websocket';

const ws = new ReconnectingWebSocket('ws://192.168.x.x:8000/ws', [], {
  connectionTimeout: 5000,
  maxRetries: 20,
});
ws.onmessage = (e) => {
  const event = JSON.parse(e.data);
  useStore.getState().handleBackendEvent(event);
};
```

> **iOS note**: On the dev build, the iOS WS client works with plain `ws://` over LAN. No cleartext config needed for iOS dev. Android dev builds require `android:usesCleartextTraffic="true"` or a network security config if targeting Android.

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `websockets` | ≥14.0 | WebSocket protocol (FastAPI internal dep) | Installed automatically with FastAPI; explicit pin avoids silent mismatches |
| `httpx` | ≥0.28 | Async HTTP client for Roboflow API calls | When using hosted Roboflow API instead of local YOLO |
| `inference` (Roboflow) | latest (`pip install inference`) | Roboflow hosted inference SDK | Only if switching to hosted CV; provides unified REST + local inference surface |
| `soundfile` | ≥0.12.1 | WAV/FLAC I/O for loading test audio clips | When feeding pre-recorded drone audio into the simulation |
| `pydantic-settings` | ≥2.0 | Config from env vars | FastAPI app config (HOST, PORT, WS_URL, model paths, API keys) |
| `pytest-asyncio` | ≥0.24 | Async test support | Testing FastAPI WebSocket endpoints and async fusion engine |
| `reconnecting-websocket` | 4.4.0 | RN auto-reconnect WS client | Add to the Expo app only if raw WS proves flaky on demo day |

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` or `pip` + `venv` | Python dependency management | `uv` is fastest for fresh installs; `requirements.txt` for reproducibility |
| `uvicorn --reload` | Hot-reload during development | `uvicorn main:app --reload --host 0.0.0.0 --port 8000` |
| `pytest` + `pytest-asyncio` | Backend test runner | `asyncio_mode = "auto"` in `pyproject.toml` |
| Python `logging` (stdlib) | Structured event logging | Use `logging.getLogger(__name__)` in each module; pipe to stdout for demo visibility |

---

## Installation

```bash
# Python backend — create venv first
python3.11 -m venv .venv && source .venv/bin/activate

# Core backbone
pip install "fastapi[standard]>=0.136.3" "uvicorn[standard]>=0.34" pydantic>=2.9 pydantic-settings>=2.0

# Acoustic DSP
pip install "librosa==0.11.0" "numpy>=2.0" "scipy>=1.15" "soundfile>=0.12.1"

# Vision (local YOLO — primary)
pip install "ultralytics==8.4.61"

# Vision (Roboflow hosted — optional/fallback)
pip install inference httpx

# Audio input (optional, for real RPi mic adapter)
pip install "sounddevice==0.5.5"

# Dev / test
pip install pytest pytest-asyncio

# React Native — add to Expo app only if reconnect needed
npx expo install reconnecting-websocket
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Local ultralytics YOLO11 | HF Inference Endpoints (hosted) | Current drone YOLO models on HF Hub explicitly say "not deployed by any Inference Provider" — no turnkey hosted API exists |
| Local ultralytics YOLO11 | AWS Rekognition / Google Vision API | Generic object detection; not drone-trained; would need custom labels or misclassify |
| Roboflow hosted API | Azure Custom Vision | More setup; no pre-trained drone model; significantly more vendor lock-in for a demo |
| librosa 0.11.0 | torchaudio | Heavier PyTorch dependency; librosa + scipy FFT is lighter and sufficient for simulation; torchaudio only needed if training a model |
| sounddevice | PyAudio | PyAudio has finicky PortAudio install on macOS/M-series Macs; sounddevice wraps the same PortAudio but with a NumPy-native API and no compile step |
| FastAPI native WebSocket | Flask-SocketIO | Wrong ecosystem; Socket.IO protocol ≠ WS; RN side would need socket.io-client; pure WS is simpler and matches RN's native API |
| asyncio tasks (single process) | Celery + Redis | Massively overkill for a single-node LAN demo; asyncio handles all concurrency needs |
| In-memory ConnectionManager | Redis Pub/Sub WS broadcast | Only needed for multi-worker/multi-node; single uvicorn worker on LAN is correct for demo |
| reconnecting-websocket (RN) | Socket.IO client | Socket.IO adds a protocol layer the FastAPI server doesn't speak |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `PyAudio` | Compile-from-source on macOS/M-series; frequent install failures; bytes-native API requires manual NumPy conversion | `sounddevice` 0.5.5 |
| `ultralytics` 8.3.41, 8.3.42, 8.3.45, 8.3.46 | Supply chain attack (Dec 2024): cryptominer payload injected via compromised CI (HiddenLayer, Snyk verified); removed from PyPI but may be cached | Pin to `==8.4.61` or use `pip install -U ultralytics` |
| `pydantic` v1 | Dropped by FastAPI 0.115+; `@validator` removed; ValidationError format changed | pydantic v2.9+ |
| HF `InferenceClient` for drone models | No HF Inference Provider currently deploys any drone YOLO model; SDK call will 404 | ultralytics local or Roboflow `inference` SDK |
| `flask-sock` / `aiohttp` WebSocket | Fragments the Python stack; FastAPI already provides first-class WebSocket support | FastAPI `@app.websocket` |
| `socket.io-client` (RN) | Binary Socket.IO protocol; incompatible with FastAPI's native WebSocket transport | Native `WebSocket` or `reconnecting-websocket` |
| `GStreamer` pipelines | Unnecessary for simulation; adds a complex native dependency | numpy sine synthesis + soundfile for recorded clips |
| `librosa.set_fftlib` | Deprecated in 0.11.0, will be removed in 1.0 | Use `scipy.fft.set_backend` if FFT backend customisation needed |

---

## Simulation Architecture Stack Pattern

```
┌─────────────────────────────────────────────────────┐
│              FastAPI process (uvicorn)               │
│                                                      │
│  AcousticSimNode  ──events──►  FusionEngine          │
│  (asyncio task)               (Pydantic models)      │
│                                    │                 │
│  VisionSimNode  ───results──►  FusionEngine          │
│  (asyncio task)                    │                 │
│                               ConnectionManager      │
│                                    │                 │
│                              WS /ws  ──JSON──►  RN   │
└─────────────────────────────────────────────────────┘
```

**AcousticSimNode**: generates synthetic audio frames with numpy (multirotor blade-pass: 50–300Hz fundamental + harmonics), extracts `librosa.feature.mfcc` (n_mfcc=20, n_fft=2048, hop_length=512), applies threshold detection, emits `AcousticEvent(confidence, freq_bands)` via asyncio Queue.

**VisionSimNode**: on acoustic trigger, loads a test drone image/video frame, runs `YOLO("sapoepsilon/yolov11s-drone-detector")` locally, emits `VisionEvent(confidence, bbox, class_name)`.

**FusionEngine**: receives both events, computes `fused = 0.6 * acoustic + 0.4 * vision`, emits `ThreatAssessment(level, confidence, recommendation)` Pydantic model via WebSocket broadcast.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `fastapi 0.136.3` | `pydantic ≥2.9, starlette ≥0.40` | v1 pydantic incompatible since 0.100 |
| `librosa 0.11.0` | `numpy ≥1.22.3 (2.0 supported), scipy ≥1.6.0` | Default FFT backend changed from numpy → scipy in 0.11.0 |
| `ultralytics 8.4.61` | `torch ≥1.8, Python ≥3.8` | Loads HF Hub models via `ultralytics/hub` format; requires internet on first load |
| `sounddevice 0.5.5` | `numpy ≥1.7, PortAudio (bundled on macOS/Windows)` | Linux may need `sudo apt-get install libportaudio2` |
| Expo SDK 56 / RN 0.85 | Native `WebSocket` (built-in) | `reconnecting-websocket` 4.x is platform-agnostic; no native module install required |

---

## Sources

- `https://pypi.org/project/fastapi/` — FastAPI 0.136.3 verified (Jun 2026) — HIGH confidence
- `https://pypi.org/project/librosa/` — librosa 0.11.0 verified (Mar 2025) — HIGH confidence
- `https://librosa.org/doc/main/changelog.html` — SciPy FFT backend change confirmed — HIGH confidence
- `https://pypi.org/project/ultralytics/` — 8.4.61 latest (Jun 2026); supply-chain warning confirmed — HIGH confidence
- `https://pypi.org/project/sounddevice/` — 0.5.5 latest — HIGH confidence
- `https://docs.roboflow.com/deploy/serverless-hosted-api-v2/pricing.md` — credit formula, latency ranges — HIGH confidence
- `https://blog.roboflow.com/serverless-inference-vision-ai-cost-comparison/` — $0.45/h at 1 req/10s (Apr 2026) — HIGH confidence
- `https://huggingface.co/sapoepsilon/yolov11s-drone-detector` — model metrics, HF Hub load syntax — HIGH confidence
- `https://github.com/pladaria/reconnecting-websocket` — RN-compatible WS reconnect — HIGH confidence
- `https://fastapi.tiangolo.com/advanced/websockets/` — ConnectionManager pattern (official) — HIGH confidence
- arXiv 2505.23782 / ASTESJ 2024 — librosa MFCC config for UAV acoustic detection — MEDIUM confidence (academic, implementation details vary)

---

*Stack research for: Sentry-CD counter-drone acoustic + vision C2 (simulated demo)*
*Researched: 2026-06-14*
