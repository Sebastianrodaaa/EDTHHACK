"""REST routes — scenario control, state snapshot, operator actions.

Routes read shared components off `app.state.ctx` (set up in main.py lifespan).
WebSocket push is the primary channel; REST is for initial snapshot, scenario
control, and operator acknowledgements (human-in-the-loop).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from models import OperatorAction

log = logging.getLogger("gateway.routes")

router = APIRouter()


def _ctx(request: Request):
    return request.app.state.ctx


@router.get("/health")
async def health(request: Request):
    ctx = _ctx(request)
    return {
        "status": "ok",
        "clients": ctx.manager.client_count,
        "scenario_active": ctx.state.scenario_active,
        "scenario_id": ctx.state.scenario_id,
    }


@router.get("/state")
async def get_state(request: Request):
    return _ctx(request).state.snapshot().model_dump()


@router.get("/scenarios")
async def list_scenarios(request: Request):
    return {"scenarios": _ctx(request).engine.list_scenarios()}


@router.post("/scenario/{scenario_id}/start")
async def start_scenario(scenario_id: str, request: Request):
    ctx = _ctx(request)
    ctx.state.reset()
    await ctx.manager.broadcast(ctx.state.snapshot().model_dump())
    ok = await ctx.engine.start(scenario_id)
    if not ok:
        return {"ok": False, "error": f"unknown scenario '{scenario_id}'"}
    return {"ok": True, "scenario_id": scenario_id}


@router.post("/scenario/stop")
async def stop_scenario(request: Request):
    ctx = _ctx(request)
    await ctx.engine.stop()
    return {"ok": True}


@router.post("/scenario/reset")
async def reset_scenario(request: Request):
    ctx = _ctx(request)
    await ctx.engine.stop()
    ctx.state.reset()
    await ctx.manager.broadcast(ctx.state.snapshot().model_dump())
    return {"ok": True}


@router.post("/operator/action")
async def operator_action(action: OperatorAction, request: Request):
    """Human-in-the-loop acknowledgement. Logged; never auto-fires effects."""
    ctx = _ctx(request)
    log.info(
        "OPERATOR ACTION action=%s assessment=%s operator=%s",
        action.action,
        action.assessment_id,
        action.operator_id,
    )
    result = await ctx.handle_operator_action(action)
    return {"ok": True, **result}
