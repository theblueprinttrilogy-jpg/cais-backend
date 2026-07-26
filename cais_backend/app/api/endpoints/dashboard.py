"""
Dashboard endpoints – REST metrics and real‑time WebSocket feed.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ---------- REST Metrics ----------
class DashboardMetrics(BaseModel):
    value_at_risk: float
    active_liens: int
    compliance_percent: float
    risk_score: float


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics() -> DashboardMetrics:
    """
    Return current dashboard metrics.
    In production, these would be fetched from a database or cache.
    """
    # Example mock data – replace with real data source
    return DashboardMetrics(
        value_at_risk=1250000.00,
        active_liens=7,
        compliance_percent=92.5,
        risk_score=4.3,
    )


# ---------- WebSocket for Real‑time Updates ----------
class ConnectionManager:
    """
    Manages active WebSocket connections and broadcasts messages.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a JSON-serializable message to all connected clients."""
        if not self.active_connections:
            return
        data = json.dumps(message)
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_text(data)
            except Exception:
                disconnected.append(conn)
        # Clean up broken connections
        async with self._lock:
            for conn in disconnected:
                if conn in self.active_connections:
                    self.active_connections.remove(conn)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming real‑time logs and status updates.
    """
    await manager.connect(websocket)
    try:
        # Send a welcome message
        await websocket.send_text(json.dumps({"type": "info", "message": "Connected to CAIS dashboard"}))
        # Keep connection alive; messages are pushed via broadcast from other parts of the system.
        while True:
            # Wait for any incoming message (client may send ping/pong)
            data = await websocket.receive_text()
            # Echo back for debugging (optional)
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        await manager.disconnect(websocket)
