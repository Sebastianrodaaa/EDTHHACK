# Phase 1 Summary: Backend Skeleton + Acoustic Simulation

**Completed:** 2026-06-14
**Status:** ✅ Verified (smoke test PASS)

## What Was Built

- `backend/models.py` — full Pydantic v2 event schema (all event types locked: acoustic, vision, fused_assessment, operator_action, state_snapshot, state_sync, track_update, reasoning trail). Single wire contract for every downstream component.
- `backend/config.py` — env-driven adapter selection + thresholds/weights (the hardware seam).
- `backend/core/event_bus.py` — in-process async pub/sub (asyncio queues, per-type fan-out).
- `backend/adapters/acoustic.py` — `AcousticAdapter` ABC + `SimulatedAcousticAdapter` synthesising realistic drone vs. ambient features.
- `backend/core/acoustic_node.py` — detection threshold + temporal gating (N consecutive frames) + cooldown; publishes `acoustic_event` and gated `vision_request`.
- `backend/core/state.py` — `SystemState` snapshot served on connect.
- `backend/sim/engine.py` + `sim/scenarios/demo_alpha.json` — scenario player owning event timing; exposes vision/track plans for later phases.
- `backend/gateway/ws.py` — `ConnectionManager` with 20-event ring buffer, snapshot-on-connect, replay-on-reconnect.
- `backend/gateway/routes.py` — `/health`, `/state`, `/scenarios`, `/scenario/{id}/start`, `/scenario/stop`, `/scenario/reset`, `/operator/action` (stub).
- `backend/main.py` — FastAPI app, lifespan wiring, `/ws` endpoint.

## Success Criteria

1. ✅ Server starts; WS connect → `state_snapshot` immediately.
2. ✅ Scenario player emits a timed acoustic_event sequence (logged, drone-like crossover at t=4s).
3. ✅ WS client receives `acoustic_event` broadcasts with full feature payload.
4. ✅ Reconnecting client receives `state_sync` replay of buffered events.

## Decisions

- Skipped `librosa` for v1 — simulated adapter synthesises features directly (lighter install, faster demo boot). Real DSP lands with `RpiAcousticAdapter`.
- Defined the **entire** event schema in Phase 1 (not just acoustic) to lock the contract and avoid cross-phase churn.
- Pydantic version pins kept as compatible ranges (`>=`) rather than the research's exact future versions, to guarantee `uv` resolution.

## Verify

```
cd backend && uv venv --python 3.11 .venv && uv pip install -r requirements.txt --python .venv
.venv/bin/python tests/smoke_phase1.py
```
