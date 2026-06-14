"""Phase 5 smoke test — target tracking + false-alarm restraint.

Verifies:
  1. A confirmed threat (demo-alpha) opens a track and emits track_update
     events with closing range + bearing.
  2. The false-alarm scenario (demo-bravo, vision=bird) keeps threat low and
     issues a non-escalating recommendation (no squad alert, no track).

Run from backend/:  python tests/smoke_phase5.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def run_until(ws, types, limit=120):
    """Read messages until all wanted types are seen or limit hit; return map."""
    found = {}
    for _ in range(limit):
        msg = ws.receive_json()
        if msg["type"] in types and msg["type"] not in found:
            found[msg["type"]] = msg
        if msg["type"] == "track_update":
            found.setdefault("_track_updates", []).append(msg)
        if all(t in found for t in types):
            break
    return found


def main() -> int:
    with TestClient(app) as client:
        # --- 1. Confirmed threat → tracking -------------------------------- #
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "state_snapshot"
            client.post("/scenario/demo-alpha/start")

            tracks = []
            assessment = None
            for _ in range(120):
                msg = ws.receive_json()
                if msg["type"] == "fused_assessment":
                    assessment = msg
                if msg["type"] == "track_update":
                    tracks.append(msg)
                    if len(tracks) >= 3:
                        break

            assert assessment is not None, "no fused_assessment"
            assert len(tracks) >= 3, f"expected >=3 track_update, got {len(tracks)}"
            ranges = [t["range_m"] for t in tracks]
            print("[1/2] track opened:", tracks[0]["track_id"],
                  "| ranges:", ranges, "| states:", [t["state"] for t in tracks])
            assert ranges[-1] < ranges[0], f"range should close: {ranges}"
            assert all("bearing_deg" in t for t in tracks)

        client.post("/scenario/reset")

        # --- 2. False alarm (bird) → restraint ----------------------------- #
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "state_snapshot"
            client.post("/scenario/demo-bravo/start")

            assessment = None
            track_seen = False
            for _ in range(80):
                msg = ws.receive_json()
                if msg["type"] == "track_update":
                    track_seen = True
                if msg["type"] == "fused_assessment":
                    assessment = msg
                    break  # bird → low threat; tracker opens only on high/critical

            assert assessment is not None, "no fused_assessment for false alarm"
            rec = assessment["recommendation"]
            print("[2/2] false alarm: threat=%s conf=%.2f rec=%s track_opened=%s" % (
                assessment["threat_level"], assessment["confidence"],
                rec["action"], track_seen))
            assert assessment["threat_level"] in ("low", "medium"), assessment
            assert rec["action"] in ("monitor", "request_visual"), rec
            assert rec["level"] < 3, rec
            assert not track_seen, "false alarm must NOT open a track"

        client.post("/scenario/reset")

    print("\nPHASE 5 SMOKE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
