from __future__ import annotations

from typing import Dict, List

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, job_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(job_id, []).append(websocket)

    def disconnect(self, job_id: int, websocket: WebSocket) -> None:
        connections = self.active_connections.get(job_id)
        if connections and websocket in connections:
            connections.remove(websocket)
            if not connections:
                self.active_connections.pop(job_id, None)

    async def send_update(self, job_id: int, message: dict) -> None:
        connections = self.active_connections.get(job_id, [])
        stale: List[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(job_id, websocket)


manager = WebSocketManager()
