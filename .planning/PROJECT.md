# Sentry-CD — Body-Worn Acoustic-Vision Counter-Drone Sentry

## What This Is

A body-worn counter-drone early-warning system. A Raspberry Pi microphone node
continuously listens for drone-like acoustic signatures; on a suspected aerial
threat it triggers a vision-analysis pipeline that pulls the live POV feed from
Meta wearable glasses (a hypothetical soldier-mounted camera) to visually confirm
and classify the object in the soldier's field of view. Acoustic and visual
evidence are fused into a confidence-based threat assessment surfaced on a mobile
command interface, which pushes escalating, human-in-the-loop recommendations
(monitor → request secondary confirmation → alert squad → prepare countermeasure
options). For this milestone the full pipeline runs as a realistic **simulated
end-to-end demo** — hardware is abstracted behind swappable adapters.

## Core Value

When a drone-like sound is detected, the operator gets a fused (sound + vision)
confidence-scored threat assessment and a clear, escalating recommendation —
fast, with the human always in control of the final action.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

> Note: An existing Expo / React Native operator command interface (the "Acoustic
> Sentry C2" app, with a Skia Liquid Glass acoustic node and an agent reasoning
> trail) already lives in this repo. It is the starting point for the mobile C2
> layer, not yet validated against the full system.

### Active

<!-- Current scope. Building toward these. -->

- [ ] Acoustic node continuously detects drone-like signatures and raises early warning
- [ ] A detection event triggers the vision pipeline to pull the glasses POV feed
- [ ] The CV layer confirms / classifies the object via a hosted pretrained model
- [ ] Late fusion combines acoustic + visual evidence into a confidence-scored threat level
- [ ] A FastAPI + WebSocket backbone streams events between node, fusion, and the app
- [ ] The mobile C2 displays live threat state, confidence, and the agent reasoning trail
- [ ] The system emits escalating recommendations with human-in-the-loop confirmation
- [ ] Simulated target tracking is maintained after confirmation
- [ ] A full simulated end-to-end demo scenario runs start to finish

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Real Raspberry Pi / Meta-glasses hardware integration — simulated this milestone; adapters keep the door open
- Actual countermeasure / effector control — recommendations only; human controls any final action (safety/ethics)
- Production security hardening and multi-user auth — demo-focused, single operator
- Cloud deployment / scaling — local LAN demo for reliability

## Context

- **Existing code:** Expo SDK 56 / React Native 0.85 (TypeScript) operator app — Skia
  + Reanimated shader-based acoustic orb (white/red states), zustand store, and a
  scripted detection-cascade reasoning trail. Runs as an iOS dev build.
- **Backbone:** FastAPI + WebSocket Python service over LAN streams sensor/fusion events.
- **Vision:** Hosted pretrained object-detection model/API for drone classification.
- **Simulation-first:** Acoustic and vision inputs are simulated behind interfaces so
  real RPi mic and Meta-glasses feeds can slot in later without rearchitecting.
- **Domain:** Counter-UAS, late sensor fusion, human-on-the-loop command & control.

## Constraints

- **Tech stack**: Mobile C2 stays Expo/React Native + Skia; backend is Python (FastAPI + websockets) — reuse the working app, iterate fast in Python.
- **Timeline**: Hackathon (EDTHHACK), time-boxed and demo-driven — favor coarse phases and simulation over hardware.
- **Hardware**: No guaranteed RPi / Meta glasses on hand — simulate with swappable adapter interfaces.
- **Human-in-the-loop**: The system never autonomously engages; the operator confirms — counter-drone safety/ethics.
- **Connectivity**: LAN / local-first for demo reliability.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Simulated end-to-end (no real hardware) | Hackathon time-box; reliable, repeatable demo | — Pending |
| FastAPI + WebSocket backbone | Simple, real-time, fast Python iteration | — Pending |
| Hosted pretrained CV model/API | Fastest path to convincing classification | — Pending |
| Reuse existing Expo RN C2 app | Already built; polished orb + reasoning trail | — Pending |
| Late fusion of acoustic + visual evidence | Matches problem framing; explainable confidence | — Pending |
| Human confirms all escalations | Keeps a human on the loop for any action | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-14 after initialization*
