"""Phase 1 smoke test — runs the app in-process via Starlette TestClient.

Verifies the four Phase 1 success criteria:
  1. WS connect yields a state_snapshot.
  2. Scenario player emits a timed acoustic_event sequence.
  3. WS client receives acoustic_event broadcasts.
  4. A reconnecting client receives a state_sync replay of recent events.

Run from backend/:  python tests/smoke_phase1.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def main() -> int:
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["status"] == "ok", health
        print("[1/4] health ok:", health)

        scenarios = client.get("/scenarios").json()["scenarios"]
        assert any(s["id"] == "demo-alpha" for s in scenarios), scenarios
        print("[ok] scenarios:", [s["id"] for s in scenarios])

        with client.websocket_connect("/ws") as ws:
            snap = ws.receive_json()
            assert snap["type"] == "state_snapshot", snap
            assert snap["orb_mode"] == "white", snap
            print("[2/4] got state_snapshot on connect:", snap["type"], snap["orb_mode"])

            client.post("/scenario/demo-alpha/start")

            acoustic = []
            drone_seen = False
            for _ in range(8):
                msg = ws.receive_json()
                if msg["type"] == "acoustic_event":
                    acoustic.append(msg)
                    if msg["classification"] == "drone_like":
                        drone_seen = True
            assert len(acoustic) >= 4, f"expected >=4 acoustic events, got {len(acoustic)}"
            print(f"[3/4] received {len(acoustic)} acoustic_event broadcasts; "
                  f"drone_like seen={drone_seen}")
            sample = acoustic[-1]
            assert set(sample["features"]) >= {
                "rms", "snr_db", "dominant_freq_hz", "band_low", "band_mid", "band_high"
            }, sample["features"]

        # Reconnect — expect snapshot + replay of recent events.
        with client.websocket_connect("/ws") as ws2:
            snap2 = ws2.receive_json()
            assert snap2["type"] == "state_snapshot", snap2
            sync = ws2.receive_json()
            assert sync["type"] == "state_sync", sync
            assert len(sync["events"]) > 0, "expected non-empty replay buffer"
            print(f"[4/4] reconnect replayed {len(sync['events'])} buffered events")

        client.post("/scenario/reset")

    print("\nPHASE 1 SMOKE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
