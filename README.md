# SENTRY-CD — Multimodal Counter-Drone C2

A React Native (Expo) command-and-control app for a **body-worn multimodal
acoustic + vision sentry** used in counter-drone defence. It fuses an acoustic
node and a POV vision node into a single threat picture with recommended
operator actions and a live event timeline.

The app ships with a built-in **simulation engine** that drives realistic
sensor data through a scripted engagement (standby → acoustic contact → vision
acquisition → confirmed threat → egress), so it runs end-to-end with no
hardware. Swap the engine for real sensor feeds when available.

## Panels

| Panel | Fields |
| --- | --- |
| **Acoustic Node** | Status (Connected/Waiting), Last Event (None/Drone-like/Noise), Confidence, RMS, Dominant Frequency, SNR |
| **POV Vision Node** | Status, Feed Type (Meta Ray-Ban POV / Uploaded / Screen Capture), Last Frame Analysis, Vision Class, Confidence |
| **Fusion Reasoning** | Threat Level, Confidence, Evidence, Recommended Operator Action |
| **Event Timeline** | Timestamp, Source, Event, Result |

## Controls

- **ARM / DISARM SENTRY** — bring the nodes online or offline.
- **INJECT DRONE** — force a high-confidence drone scenario for demos.
- **Feed source toggle** — switch the vision feed (Ray-Ban / Upload / Screen).

## Run

```bash
npm install
npm run web      # browser
npm run ios      # iOS simulator
npm run android  # Android emulator
```

## Architecture

```
src/
  types.ts                  domain model
  theme.ts                  tactical dark theme + threat/status colors
  sim/
    engine.ts               scripted scenario + sensor sampling (with jitter)
    fusion.ts               late-fusion threat reasoning + recommended actions
  store/useSentryStore.ts   zustand store + 1 Hz simulation loop
  components/               Header, ControlBar, AcousticNode, VisionNode,
                            FusionPanel, Timeline, shared primitives
  screens/CommandScreen.tsx responsive 1-/2-column dashboard
```

### Wiring in real sensors

Replace the `sampleAcoustic` / `sampleVision` calls in
`src/store/useSentryStore.ts` with your sensor adapters, push real readings into
the store, and `fuse()` in `src/sim/fusion.ts` will produce the threat
assessment unchanged.
