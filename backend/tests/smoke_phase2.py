"""Phase 2 smoke test — acoustic→vision trigger end-to-end.

Verifies:
  1. A sustained drone-like acoustic cascade triggers a vision analysis.
  2. The Vision Worker publishes a vision_event linked to the triggering
     acoustic event (trigger_acoustic_id), with a classification + confidence.

Run from backend/:  python tests/smoke_phase2.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def main() -> int:
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            snap = ws.receive_json()
            assert snap["type"] == "state_snapshot", snap

            client.post("/scenario/demo-alpha/start")

            vision_event = None
            acoustic_ids = set()
            for _ in range(40):
                msg = ws.receive_json()
                if msg["type"] == "acoustic_event":
                    acoustic_ids.add(msg["id"])
                elif msg["type"] == "vision_event":
                    vision_event = msg
                    break
                elif msg["type"] == "vision_timeout":
                    raise AssertionError(f"unexpected vision_timeout: {msg}")

            assert vision_event is not None, "no vision_event received from cascade"
            print("[1/2] acoustic cascade triggered vision analysis")
            print("[ok] vision_event:", {
                "class": vision_event["classification"],
                "conf": vision_event["confidence"],
                "bbox": vision_event["bounding_box"] is not None,
            })
            assert vision_event["classification"] == "drone", vision_event
            assert vision_event["confidence"] >= 0.8, vision_event
            assert vision_event["trigger_acoustic_id"] in acoustic_ids, (
                "vision_event not linked to a broadcast acoustic_event"
            )
            print("[2/2] vision_event linked to triggering acoustic_event")

        client.post("/scenario/reset")

    print("\nPHASE 2 SMOKE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
