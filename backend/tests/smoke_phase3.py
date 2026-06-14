"""Phase 3 smoke test — fusion, escalation recommendation, operator HITL.

Verifies:
  1. vision_event → fused_assessment with weighted confidence + threat level.
  2. Recommendation escalates to an actionable level requiring confirmation.
  3. Operator 'confirm' is recorded in the audit log and clears confirmation.
  4. Operator 'stand_down' clears the threat (orb back to white).

Run from backend/:  python tests/smoke_phase3.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def main() -> int:
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "state_snapshot"
            client.post("/scenario/demo-alpha/start")

            assessment = None
            orb_red_seen = False
            for _ in range(60):
                msg = ws.receive_json()
                if msg["type"] == "state_snapshot" and msg["orb_mode"] == "red":
                    orb_red_seen = True
                if msg["type"] == "fused_assessment":
                    assessment = msg
                    break
            assert orb_red_seen, "orb never went red (early warning missing)"
            assert assessment is not None, "no fused_assessment produced"
            print("[1/4] fused_assessment:", {
                "threat": assessment["threat_level"],
                "conf": assessment["confidence"],
                "acoustic": assessment["acoustic_confidence"],
                "vision": assessment["vision_confidence"],
                "source": assessment["source_mode"],
            })
            assert assessment["source_mode"] == "fused", assessment
            assert assessment["threat_level"] in ("high", "critical"), assessment
            rec = assessment["recommendation"]
            print("[2/4] recommendation:", rec["level"], rec["action"],
                  "| confirm?", rec["requires_confirmation"])
            assert rec["level"] >= 3, rec
            assert rec["requires_confirmation"] is True, rec
            assert assessment["tracking"]["bearing_deg"] == 312.0, assessment["tracking"]

            aid = assessment["id"]
            client.post("/operator/action", json={
                "type": "operator_action", "action": "confirm",
                "assessment_id": aid, "operator_id": "op-1"})

        audit = client.get("/audit").json()["audit_log"]
        assert any(e["action"] == "confirm" for e in audit), audit
        print(f"[3/4] operator confirm recorded in audit log ({len(audit)} entries)")

        # stand_down clears the threat.
        client.post("/operator/action", json={
            "type": "operator_action", "action": "stand_down", "operator_id": "op-1"})
        state = client.get("/state").json()
        assert state["orb_mode"] == "white", state
        assert state["threat_level"] == "low", state
        print("[4/4] stand_down cleared threat (orb white, threat low)")

        client.post("/scenario/reset")

    print("\nPHASE 3 SMOKE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
