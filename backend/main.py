"""Sentry-CD backend — FastAPI app, component wiring, and WebSocket endpoint.

Wires the in-process pipeline:

    ScenarioEngine → AcousticAdapter → AcousticNode → EventBus → Gateway → WS

Vision worker, fusion engine, and tracking are added to this context in later
phases. The architecture keeps each seam adapter-agnostic, so wiring grows by
addition, not rewrite.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import config
from adapters.acoustic import SimulatedAcousticAdapter
from core.acoustic_node import AcousticNode
from core.event_bus import EventBus
from core.state import SystemState
from gateway.routes import router
from gateway.ws import ConnectionManager
from models import OperatorAction
from sim.engine import ScenarioEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-18s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


class AppContext:
    """Holds the wired pipeline so routes/WS handlers can reach components."""

    def __init__(self) -> None:
        self.bus = EventBus()
        self.state = SystemState()
        self.acoustic_adapter = (
            SimulatedAcousticAdapter()
            if config.ACOUSTIC_ADAPTER == "simulated"
            else SimulatedAcousticAdapter()  # real adapters land in later work
        )
        self.acoustic_node = AcousticNode(self.bus)
        self.engine = ScenarioEngine(
            self.acoustic_adapter, self.acoustic_node, self.state
        )
        self.manager = ConnectionManager(self.bus, self.state)

    def start(self) -> None:
        self.manager.start_pumps()

    async def shutdown(self) -> None:
        await self.engine.stop()
        await self.manager.stop_pumps()

    async def handle_operator_action(self, action: OperatorAction) -> dict:
        # Escalation handling is added in Phase 3. For now, acknowledge only.
        return {"handled": action.action}


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = AppContext()
    app.state.ctx = ctx
    ctx.start()
    log.info("Sentry-CD backend online — adapters: acoustic=%s vision=%s",
             config.ACOUSTIC_ADAPTER, config.VISION_ADAPTER)
    yield
    await ctx.shutdown()
    log.info("Sentry-CD backend shutdown complete")


app = FastAPI(title="Sentry-CD Gateway", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    ctx: AppContext = ws.app.state.ctx
    await ctx.manager.connect(ws)
    try:
        while True:
            # Clients may push operator_action over WS as well as REST.
            msg = await ws.receive_json()
            if msg.get("type") == "operator_action":
                try:
                    action = OperatorAction(**msg)
                    await ctx.handle_operator_action(action)
                except Exception as exc:  # noqa: BLE001
                    log.warning("bad operator_action over ws: %s", exc)
    except WebSocketDisconnect:
        ctx.manager.disconnect(ws)
    except Exception as exc:  # noqa: BLE001
        log.warning("ws error: %s", exc)
        ctx.manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
