"""WebSocket gateway — session registry, ring buffer, and event fan-out.

The single external fan-out point. Backend components publish to the EventBus;
this manager pumps those events to every connected mobile client. A bounded
ring buffer lets a reconnecting client replay the last N events so it never
shows a blank screen mid-scenario.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque

from fastapi import WebSocket

import config
from core.event_bus import EventBus
from core.state import SystemState
from models import StateSync

log = logging.getLogger("gateway.ws")

# Event types broadcast to mobile clients.
BROADCAST_TYPES = [
    "acoustic_event",
    "vision_event",
    "vision_timeout",
    "fused_assessment",
    "track_update",
    "state_snapshot",
]


class ConnectionManager:
    def __init__(self, bus: EventBus, state: SystemState) -> None:
        self.bus = bus
        self.state = state
        self._connections: set[WebSocket] = set()
        self._buffer: deque[dict] = deque(maxlen=config.EVENT_BUFFER_SIZE)
        self._pumps: list[asyncio.Task] = []

    # -- lifecycle -------------------------------------------------------- #
    def start_pumps(self) -> None:
        for event_type in BROADCAST_TYPES:
            self._pumps.append(asyncio.create_task(self._pump(event_type)))

    async def stop_pumps(self) -> None:
        for task in self._pumps:
            task.cancel()
        for task in self._pumps:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._pumps.clear()

    async def _pump(self, event_type: str) -> None:
        async for payload in self.bus.stream(event_type):
            await self.broadcast(payload)

    # -- connections ------------------------------------------------------ #
    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        # 1) current state snapshot, 2) replay recent events.
        await self._send(ws, self.state.snapshot().model_dump())
        if self._buffer:
            sync = StateSync(events=list(self._buffer))
            await self._send(ws, sync.model_dump())
        log.info("client connected (%d total)", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        log.info("client disconnected (%d total)", len(self._connections))

    # -- broadcast -------------------------------------------------------- #
    async def broadcast(self, payload: dict) -> None:
        # state_snapshot is point-in-time; don't pollute the replay buffer.
        if payload.get("type") != "state_snapshot":
            self._buffer.append(payload)
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001 — client vanished mid-send
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def _send(self, ws: WebSocket, payload: dict) -> None:
        try:
            await ws.send_json(payload)
        except Exception:  # noqa: BLE001
            self.disconnect(ws)

    @property
    def client_count(self) -> int:
        return len(self._connections)
