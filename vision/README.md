# Live classification overlay (Sentry-CD vision)

Real-time object identification + classification overlay for the demo. Runs two
YOLO11 models per frame and draws boxes/labels with Roboflow `supervision`:

- **COCO YOLO11n** — general objects (person, car, …). Aerial classes
  (`airplane`, `bird`, `kite`) are flagged red as threats.
- **Drone YOLO11** (`SkyGuardAI/drone-detection-yolov11`) — drone-specific, also red.

When the drone model sees a drone, the overlay POSTs the detection to the
Sentry-CD backend (`/api/vision/detection`). The mobile C2 app then escalates to
`critical`, completes the agent reasoning trace, and shows the staged
counter-UAS resource package.

## Run on the live Ray-Ban / WhatsApp call

1. Join the WhatsApp video call in **WhatsApp Desktop** on this Mac so the
   Ray-Ban POV is visible in a window.
2. Grant **Screen Recording** permission to your terminal app:
   System Settings → Privacy & Security → Screen Recording → enable Terminal/iTerm,
   then fully quit and reopen it (one-time).
3. Start the viewer and drag a box around the call window:

```bash
cd vision
.venv/bin/python live_overlay.py
```

Keep the backend and mobile app running in separate terminals:

```bash
cd backend
.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

A picker appears: drag a box around the video region, press **ENTER**. The
overlay window then tracks that region live.

### Options

```bash
.venv/bin/python live_overlay.py --full            # capture whole primary monitor
.venv/bin/python live_overlay.py --monitor 2       # use a second display
.venv/bin/python live_overlay.py --no-drone        # COCO only (faster)
.venv/bin/python live_overlay.py --source clip.mp4 # test on a recorded file (loops)
.venv/bin/python live_overlay.py --no-backend      # overlay only; don't drive C2
```

Keys: `q`/`ESC` quit · `r` re-select region · `space` pause · `s` save snapshot.

## Notes

- This is an **Intel Mac**, so inference runs on CPU. Frames are downscaled to
  `--max-width 1280` and `--imgsz 640` to stay interactive (~several FPS with both
  models; use `--no-drone` for higher FPS).
- Pinned stack (Intel-Mac compatible): `torch==2.2.2`, `numpy<2`,
  `opencv-python==4.10.0.84`. See `requirements.txt`.
- Models live in `vision/models/`.
