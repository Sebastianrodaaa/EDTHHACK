# Expo HAS CHANGED

Read the exact versioned docs at https://docs.expo.dev/versions/v56.0.0/ before writing any code.

# Project: Sentry-CD

Body-worn acoustic-vision counter-drone sentry, built as a simulated end-to-end demo.
Acoustic detection → vision confirmation → late fusion → escalating, human-on-the-loop
recommendations on a mobile command interface.

**Architecture:** FastAPI + WebSocket Python backbone (LAN) streaming events to the
existing Expo / React Native (TypeScript, Skia) operator app. Sensor inputs sit behind
swappable adapters (simulated now; real Raspberry Pi mic + Meta glasses later). Vision
uses a pretrained detector with a CV mock mode for demo reliability.

**Non-negotiables (from research):** scripted/deterministic scenario player, fusion
confidence calibration before any confidence UI, WebSocket replay buffer + state-sync on
reconnect, honest "human-on-the-loop" framing (DISMISS as prominent as CONFIRM), and
NEVER autonomous countermeasure engagement.

## GSD Workflow

This project is managed with GSD. Planning artifacts live in `.planning/`:

- `PROJECT.md` — project context, core value, constraints, key decisions
- `REQUIREMENTS.md` — v1 requirements (REQ-IDs) + traceability to phases
- `ROADMAP.md` — 5 phases, success criteria, requirement mapping
- `STATE.md` — current project memory / focus
- `research/` — STACK, FEATURES, ARCHITECTURE, PITFALLS, SUMMARY
- `config.json` — workflow config (mode: yolo, granularity: coarse, research on)

Phases run in order 1 → 5. Use `/gsd:plan-phase N` to plan, then `/gsd:execute-phase N`.
Read PROJECT.md and the relevant research files before planning or executing a phase.
