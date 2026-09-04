import logging
from typing import Dict, Set
from fastapi import WebSocket
from app.schemas.events import EventEnvelope

logger = logging.getLogger("samved.realtime")


class ConnectionManager:
    """Manages active WebSocket connections mapped by session_id."""

    def __init__(self):
        self.active_sessions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = set()
        self.active_sessions[session_id].add(websocket)
        logger.info(f"WebSocket connected for session {session_id}. Total sessions: {len(self.active_sessions)}")

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        if session_id in self.active_sessions:
            self.active_sessions[session_id].discard(websocket)
            if not self.active_sessions[session_id]:
                del self.active_sessions[session_id]
        logger.info(f"WebSocket disconnected for session {session_id}. Remaining sessions: {len(self.active_sessions)}")

    async def send_personal_envelope(self, websocket: WebSocket, envelope: EventEnvelope) -> None:
        await websocket.send_text(envelope.model_dump_json())

    async def broadcast_to_session(self, session_id: str, envelope: EventEnvelope) -> None:
        if session_id in self.active_sessions:
            text_data = envelope.model_dump_json()
            dead_connections = set()
            for ws in self.active_sessions[session_id]:
                try:
                    await ws.send_text(text_data)
                except Exception:
                    dead_connections.add(ws)
            for dead_ws in dead_connections:
                self.disconnect(dead_ws, session_id)

    @property
    def total_active_connections(self) -> int:
        return sum(len(conns) for conns in self.active_sessions.values())


manager = ConnectionManager()
