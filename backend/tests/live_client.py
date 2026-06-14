"""Live network smoke — connects to a running uvicorn over real ws:// + http://.

Mirrors what the mobile app's useServerEvents hook + REST api do, validating the
end-to-end transport contract the Phase 4 UI relies on.

Prereq: uvicorn running on 127.0.0.1:8000.
Run from backend/:  python tests/live_client.py
"""

import asyncio
import json
import urllib.request

import websockets

BASE = "http://127.0.0.1:8000"
WS = "ws://127.0.0.1:8000/ws"


def post(path: str) -> dict:
    req = urllib.request.Request(BASE + path, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


async def main() -> int:
    async with websockets.connect(WS) as ws:
        snap = json.loads(await ws.recv())
        assert snap["type"] == "state_snapshot", snap
        print("[connect] state_snapshot orb=%s threat=%s" % (
            snap["orb_mode"], snap["threat_level"]))

        post("/scenario/demo-alpha/start")

        seen = set()
        assessment = None
        for _ in range(80):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            seen.add(msg["type"])
            if msg["type"] == "fused_assessment":
                assessment = msg
                break

        assert assessment is not None, f"no fused_assessment; saw {seen}"
        print("[stream] event types seen:", sorted(seen))
        print("[result] threat=%s conf=%.2f rec=%s confirm=%s" % (
            assessment["threat_level"], assessment["confidence"],
            assessment["recommendation"]["action"],
            assessment["recommendation"]["requires_confirmation"]))

        # Operator confirm over REST (as the app's ThreatPanel does).
        post("/operator/action") if False else None
        import urllib.request as u
        body = json.dumps({"type": "operator_action", "action": "confirm",
                           "assessment_id": assessment["id"], "operator_id": "op-1"}).encode()
        req = u.Request(BASE + "/operator/action", data=body,
                        headers={"Content-Type": "application/json"}, method="POST")
        with u.urlopen(req, timeout=5) as r:
            print("[action] confirm ->", json.loads(r.read()))

        post("/scenario/reset")

    print("\nPHASE 4 LIVE TRANSPORT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
