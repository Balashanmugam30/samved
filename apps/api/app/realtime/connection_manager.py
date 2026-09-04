import logging
from typing import Dict, Optional, Set
from fastapi import WebSocket
from app.schemas.events import EventEnvelope

logger = logging.getLogger("samved.realtime")


class ConnectionManager:
    """Manages active WebSocket connections mapped by session_id and operator subscribers."""

    def __init__(self):
        self.active_sessions: Dict[str, Set[WebSocket]] = {}
        # Operator connections: maps WebSocket -> subscribed call_id (or None for ALL)
        self.operator_subscribers: Dict[WebSocket, Optional[str]] = {}

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

    def register_operator(self, websocket: WebSocket, call_id: Optional[str] = None) -> None:
        """Registers an operator WebSocket connection with an optional call_id filter."""
        self.operator_subscribers[websocket] = call_id
        logger.info(
            f"Operator WebSocket registered (filter={call_id or 'ALL'}). Total operators: {len(self.operator_subscribers)}"
        )

    def unregister_operator(self, websocket: WebSocket) -> None:
        """Unregisters an operator WebSocket connection."""
        if websocket in self.operator_subscribers:
            del self.operator_subscribers[websocket]
            logger.info(f"Operator WebSocket unregistered. Remaining operators: {len(self.operator_subscribers)}")

    def subscribe_operator(self, websocket: WebSocket, call_id: Optional[str]) -> None:
        """Updates subscription filter for a connected operator client."""
        if websocket in self.operator_subscribers:
            self.operator_subscribers[websocket] = call_id
            logger.info(f"Operator subscription updated to {call_id or 'ALL'}")

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

    async def broadcast_to_operators(self, envelope: EventEnvelope) -> None:
        """Broadcasts an event envelope to operator clients respecting subscription filters."""
        if not self.operator_subscribers:
            return

        text_data = envelope.model_dump_json()
        dead_operators = []

        for ws, target_call_id in list(self.operator_subscribers.items()):
            # Send if operator subscribed to ALL (None) or target_call_id matches envelope.call_id
            # Also send if envelope is global (no call_id or call_id == "global" or call_id == "system")
            should_send = (
                target_call_id is None
                or not envelope.call_id
                or envelope.call_id in ("global", "system")
                or target_call_id == envelope.call_id
            )
            if should_send:
                try:
                    await ws.send_text(text_data)
                except Exception:
                    dead_operators.append(ws)

        for dead_ws in dead_operators:
            self.unregister_operator(dead_ws)

    async def broadcast_global(self, envelope: EventEnvelope) -> None:
        """Broadcasts an event envelope to session WebSockets and operator WebSockets."""
        text_data = envelope.model_dump_json()
        dead_connections = []
        for sid, conns in list(self.active_sessions.items()):
            for ws in list(conns):
                try:
                    await ws.send_text(text_data)
                except Exception:
                    dead_connections.append((ws, sid))
        for dead_ws, sid in dead_connections:
            self.disconnect(dead_ws, sid)

        # Also send to operator subscribers
        await self.broadcast_to_operators(envelope)

    @property
    def total_active_connections(self) -> int:
        return sum(len(conns) for conns in self.active_sessions.values())

    @property
    def total_operators(self) -> int:
        return len(self.operator_subscribers)


manager = ConnectionManager()

