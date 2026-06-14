# Phase 2 Summary: Vision Pipeline + CV Mock

**Completed:** 2026-06-14
**Status:** ✅ Verified (smoke test PASS)

## What Was Built

- `backend/adapters/vision.py` — `VisionAdapter` ABC, `SimulatedVisionAdapter` (CV_MOCK_MODE = `scripted` pulls from the active scenario's vision plan; `random` fabricates a plausible result with latency), and a stubbed `HostedCVModelAdapter` seam for a hosted detector.
- `backend/core/vision_worker.py` — consumes `vision_request`, calls the adapter under a hard `VISION_TIMEOUT_S` guard, publishes `vision_event` or `vision_timeout`, and tracks the vision subsystem status (`active`/`online`/`degraded`).
- `backend/main.py` — wired the vision adapter (scripted from scenario) + worker into `AppContext`; worker loop starts on lifespan.

## Success Criteria

1. ✅ A sustained drone-like acoustic cascade triggers vision analysis (temporal gate → `vision_request`).
2. ✅ Vision Worker publishes `vision_event` (class=drone, conf=0.91, bbox present) linked via `trigger_acoustic_id` to the triggering acoustic event.
3. ✅ Timeout path implemented (`vision_timeout` + `degraded` subsystem) for slow/dead CV.

## Decisions

- Adapter latency simulated with `asyncio.sleep` (never blocks the event loop — Anti-Pattern 4 avoided).
- Scripted responses injected via a `response_provider` callable so the worker stays adapter-agnostic; swapping to `HostedCVModelAdapter` needs no worker changes.

## Verify

```
cd backend && .venv/bin/python tests/smoke_phase2.py
```
