"""
Live object identification + classification overlay.

Captures a screen region (e.g. a WhatsApp Desktop video-call window streaming the
Meta Ray-Ban POV) or a video file, runs two YOLO11 models per frame
(general COCO + a drone-specific detector), and draws a real-time
supervision overlay. Aerial / drone detections are flagged as threats.

Usage:
    # interactive: drag a box around the WhatsApp call window, then it runs
    .venv/bin/python live_overlay.py

    # capture a whole monitor (1 = primary)
    .venv/bin/python live_overlay.py --monitor 1 --full

    # test against a recorded clip instead of the screen
    .venv/bin/python live_overlay.py --source /path/to/clip.mp4

Keys (in the viewer window):
    q / ESC  quit      r  re-select region      s  save snapshot      space  pause
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path

import cv2
import numpy as np
import requests
import supervision as sv
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
MODELS = HERE / "models"
log = logging.getLogger("vision.overlay")

# COCO classes that are plausible aerial threats from a head-mounted POV.
AERIAL_COCO = {"airplane", "aeroplane", "bird", "kite"}
VISION_CLASS_MAP = {
    "drone": "drone",
    "airplane": "aircraft",
    "aeroplane": "aircraft",
    "bird": "bird",
}

THREAT_COLOR = sv.Color(r=255, g=59, b=48)   # iOS system red
SAFE_COLOR = sv.Color(r=48, g=209, b=88)     # iOS system green


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Live YOLO + supervision overlay")
    p.add_argument("--source", default="screen",
                   help="'screen' (default) or a path to a video file")
    p.add_argument("--monitor", type=int, default=1,
                   help="monitor index for screen capture (1 = primary)")
    p.add_argument("--full", action="store_true",
                   help="capture the whole monitor (skip ROI selection)")
    p.add_argument("--region", default=None,
                   help="screen region as 'left,top,width,height' (skips ROI picker)")
    p.add_argument("--coco-weights", default=str(MODELS / "yolo11n.pt"))
    p.add_argument("--drone-weights", default=str(MODELS / "drone_yolo11.pt"))
    p.add_argument("--conf", type=float, default=0.35, help="COCO confidence threshold")
    p.add_argument("--drone-conf", type=float, default=0.30, help="drone confidence threshold")
    p.add_argument("--imgsz", type=int, default=640, help="inference image size")
    p.add_argument("--max-width", type=int, default=1280,
                   help="downscale captured frames wider than this before inference")
    p.add_argument("--no-drone", action="store_true", help="disable the drone model")
    p.add_argument("--backend-url", default="http://localhost:8000",
                   help="Sentry-CD backend base URL")
    p.add_argument("--api-key", default=os.getenv("LIVE_CV_INGEST_KEY", ""),
                   help="optional x-api-key for /api/vision/detection")
    p.add_argument("--post-interval", type=float, default=2.0,
                   help="minimum seconds between backend detection posts")
    p.add_argument("--no-backend", action="store_true",
                   help="draw overlay only; do not post detections to backend")
    return p.parse_args()


def select_region(sct, monitor: dict) -> dict:
    """Grab one full-monitor frame and let the user drag a capture box."""
    shot = np.array(sct.grab(monitor))
    frame = cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)
    win = "Drag a box around the video, then ENTER (or C to cancel = full screen)"
    x, y, w, h = cv2.selectROI(win, frame, showCrosshair=False, fromCenter=False)
    cv2.destroyWindow(win)
    if w == 0 or h == 0:
        return monitor
    return {"left": monitor["left"] + int(x), "top": monitor["top"] + int(y),
            "width": int(w), "height": int(h)}


class ScreenSource:
    def __init__(self, monitor_index: int, full: bool, region: str | None):
        import mss  # imported lazily so video-file mode needs no screen perms
        self.sct = mss.mss()
        monitor = self.sct.monitors[monitor_index]
        if region:
            l, t, w, h = (int(v) for v in region.split(","))
            self.region = {"left": l, "top": t, "width": w, "height": h}
        elif full:
            self.region = monitor
        else:
            self.region = select_region(self.sct, monitor)

    def read(self):
        shot = np.array(self.sct.grab(self.region))
        return True, cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)

    def reselect(self):
        full = self.sct.monitors[1]
        self.region = select_region(self.sct, full)

    def release(self):
        pass


class VideoSource:
    def __init__(self, path: str):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise SystemExit(f"Could not open video: {path}")

    def read(self):
        ok, frame = self.cap.read()
        if not ok:  # loop the clip
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
        return ok, frame

    def reselect(self):
        pass

    def release(self):
        self.cap.release()


def split_detections(det: sv.Detections, threat_names: set[str]):
    """Split a Detections set into (threats, safe) by class_name."""
    names = det.data.get("class_name")
    if names is None or len(det) == 0:
        return det[np.zeros(len(det), dtype=bool)], det
    mask = np.array([str(n).lower() in threat_names for n in names], dtype=bool)
    return det[mask], det[~mask]


def labels_for(det: sv.Detections) -> list[str]:
    names = det.data.get("class_name", [""] * len(det))
    return [f"{n} {c:.2f}" for n, c in zip(names, det.confidence)]


def detection_payload(det: sv.Detections, frame_shape: tuple[int, int, int]) -> dict | None:
    """Return the highest-confidence live-CV payload for backend ingestion."""
    if len(det) == 0:
        return None
    names = det.data.get("class_name")
    if names is None:
        return None

    # Prefer drone detections over generic aerial objects.
    candidates = []
    for idx, name in enumerate(names):
        raw = str(name).lower()
        mapped = VISION_CLASS_MAP.get(raw)
        if mapped is None:
            continue
        priority = 1 if mapped == "drone" else 0
        candidates.append((priority, float(det.confidence[idx]), idx, mapped))
    if not candidates:
        return None

    _, conf, idx, classification = max(candidates)
    h, w = frame_shape[:2]
    x1, y1, x2, y2 = det.xyxy[idx]
    bw = max(1.0, float(x2 - x1))
    bh = max(1.0, float(y2 - y1))
    cx = (float(x1) + float(x2)) / 2.0
    # Approximate phone/glasses horizontal FOV: center = 0°, right = +35°.
    bearing_deg = ((cx / max(1, w)) - 0.5) * 70.0

    return {
        "type": "vision_detection",
        "source": "live_overlay",
        "classification": classification,
        "confidence": round(conf, 3),
        "bearing_deg": round(bearing_deg, 1),
        "bounding_box": {
            "x": round(float(x1) / w, 4),
            "y": round(float(y1) / h, 4),
            "w": round(bw / w, 4),
            "h": round(bh / h, 4),
        },
    }


def post_detection(backend_url: str, payload: dict, api_key: str = "") -> bool:
    headers = {"x-api-key": api_key} if api_key else None
    try:
        res = requests.post(
            f"{backend_url.rstrip('/')}/api/vision/detection",
            json=payload,
            headers=headers,
            timeout=0.5,
        )
        if res.ok:
            data = res.json()
            if data.get("escalated"):
                log.info(
                    "C2 DISPATCH: %s %s",
                    data.get("threat_level"),
                    data.get("dispatch", {}).get("effector"),
                )
            return True
        log.warning("backend rejected detection: %s %s", res.status_code, res.text[:160])
    except requests.RequestException as exc:
        log.warning("backend post failed: %s", exc)
    return False


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    coco = YOLO(args.coco_weights)
    drone = None if args.no_drone else YOLO(args.drone_weights)

    if args.source == "screen":
        src = ScreenSource(args.monitor, args.full, args.region)
    else:
        src = VideoSource(args.source)

    box_safe = sv.BoxAnnotator(color=SAFE_COLOR, thickness=2)
    box_threat = sv.BoxAnnotator(color=THREAT_COLOR, thickness=3)
    label_safe = sv.LabelAnnotator(color=SAFE_COLOR, text_scale=0.5, text_thickness=1)
    label_threat = sv.LabelAnnotator(color=THREAT_COLOR, text_scale=0.6, text_thickness=2)

    win = "Sentry-CD  |  live classification"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    fps_ema, paused, last = 0.0, False, None
    last_backend_post = 0.0

    while True:
        if not paused:
            ok, frame = src.read()
            if not ok:
                break

            # downscale wide frames so CPU inference stays interactive
            if frame.shape[1] > args.max_width:
                scale = args.max_width / frame.shape[1]
                frame = cv2.resize(frame, None, fx=scale, fy=scale,
                                   interpolation=cv2.INTER_AREA)

            t0 = time.time()
            r_coco = coco.predict(frame, imgsz=args.imgsz, conf=args.conf,
                                  device="cpu", verbose=False)[0]
            coco_det = sv.Detections.from_ultralytics(r_coco)
            threat, safe = split_detections(coco_det, AERIAL_COCO)

            if drone is not None:
                r_drone = drone.predict(frame, imgsz=args.imgsz, conf=args.drone_conf,
                                        device="cpu", verbose=False)[0]
                drone_det = sv.Detections.from_ultralytics(r_drone)
                threat = sv.Detections.merge([threat, drone_det]) if len(drone_det) else threat

            dt = time.time() - t0
            fps_ema = (1.0 / dt) if fps_ema == 0 else 0.9 * fps_ema + 0.1 * (1.0 / dt)

            out = frame.copy()
            if len(safe):
                out = box_safe.annotate(out, safe)
                out = label_safe.annotate(out, safe, labels_for(safe))
            if len(threat):
                out = box_threat.annotate(out, threat)
                out = label_threat.annotate(out, threat, labels_for(threat))

            if not args.no_backend and len(threat):
                now = time.time()
                if now - last_backend_post >= args.post_interval:
                    payload = detection_payload(threat, frame.shape)
                    if payload and payload["classification"] == "drone":
                        last_backend_post = now
                        post_detection(args.backend_url, payload, args.api_key)

            _draw_hud(out, fps_ema, len(safe), len(threat))
            last = out

        if last is not None:
            cv2.imshow(win, last)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("r"):
            src.reselect()
        if key == ord(" "):
            paused = not paused
        if key == ord("s") and last is not None:
            fn = HERE / f"snapshot_{int(time.time())}.jpg"
            cv2.imwrite(str(fn), last)
            print(f"saved {fn}")

    src.release()
    cv2.destroyAllWindows()


def _draw_hud(img, fps: float, n_safe: int, n_threat: int) -> None:
    h, w = img.shape[:2]
    cv2.rectangle(img, (0, 0), (w, 34), (24, 24, 28), -1)
    cv2.putText(img, f"{fps:4.1f} FPS   objects:{n_safe}", (12, 23),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (235, 235, 235), 1, cv2.LINE_AA)
    if n_threat > 0:
        txt = f"AERIAL THREAT x{n_threat}"
        (tw, _), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(img, (w - tw - 24, 0), (w, 34), (48, 59, 255), -1)
        cv2.putText(img, txt, (w - tw - 12, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)


if __name__ == "__main__":
    main()
