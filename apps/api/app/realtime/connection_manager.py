import asyncio
import json
import logging
import uuid
from typing import Dict, Optional, Set
from fastapi import WebSocket
from app.schemas.events import EventEnvelope

logger = logging.getLogger("samved.realtime")


class ConnectionManager:
    """Manages active WebSocket connections mapped by session_id and operator subscribers.

    Supports cross-instance event fanout via Redis Pub/Sub for multi-instance Vercel deployments.
    """

    def __init__(self):
        self.instance_id = f"inst-{uuid.uuid4().hex[:8]}"
        self.active_sessions: Dict[str, Set[WebSocket]] = {}
        # Operator connections: maps WebSocket -> subscribed call_id (or None for ALL)
        self.operator_subscribers: Dict[WebSocket, Optional[str]] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._pubsub_client: Optional[Any] = None
        self._is_listening = False

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

    async def _dispatch_to_local_operators(self, envelope: EventEnvelope) -> None:
        """Dispatches an event envelope directly to local operator clients."""
        if not self.operator_subscribers:
            return

        text_data = envelope.model_dump_json()
        dead_operators = []

        for ws, target_call_id in list(self.operator_subscribers.items()):
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

    async def broadcast_to_operators(self, envelope: EventEnvelope, publish_redis: bool = True) -> None:
        """Broadcasts an event envelope to operator clients.

        Also publishes to Redis for cross-instance fanout if publish_redis is True.
        """
        # 1. Local delivery first
        await self._dispatch_to_local_operators(envelope)

        # 2. Redis cross-instance publish (non-blocking)
        if publish_redis:
            try:
                from app.core.redis import publish_operator_event
                asyncio.create_task(
                    publish_operator_event(
                        envelope_json=envelope.model_dump_json(),
                        origin_id=self.instance_id,
                    )
                )
            except Exception as e:
                logger.debug(f"Redis operator publish error: {e}")

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

        # Also send to operator subscribers (local and Redis pub/sub)
        await self.broadcast_to_operators(envelope, publish_redis=True)

    def start_redis_listener(self) -> None:
        """Launches the background Redis pub/sub listener for cross-instance operator events."""
        if self._is_listening:
            return
        self._is_listening = True
        self._listener_task = asyncio.create_task(self._redis_listen_loop())
        logger.info(f"Started Redis operator event listener (Instance: {self.instance_id})")

    async def stop_redis_listener(self) -> None:
        """Gracefully stops the background Redis pub/sub listener."""
        self._is_listening = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._pubsub_client is not None:
            try:
                await self._pubsub_client.close()
            except Exception:
                pass
            self._pubsub_client = None
        logger.info("Stopped Redis operator event listener.")

    async def _redis_listen_loop(self) -> None:
        """Background loop reading operator events from Redis pub/sub."""
        from app.core.redis import get_redis_client, OPERATOR_EVENT_CHANNEL

        while self._is_listening:
            client = await get_redis_client()
            if client is None:
                await asyncio.sleep(2.0)
                continue

            pubsub = client.pubsub()
            self._pubsub_client = pubsub
            try:
                await pubsub.subscribe(OPERATOR_EVENT_CHANNEL)
                logger.info(f"Subscribed to Redis channel '{OPERATOR_EVENT_CHANNEL}'")

                while self._is_listening:
                    try:
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                        if message and message.get("type") == "message":
                            raw_data = message.get("data")
                            if raw_data:
                                try:
                                    parsed = json.loads(raw_data)
                                    origin_id = parsed.get("origin_id")
                                    # Ignore events that originated from this instance (prevent duplicate delivery)
                                    if origin_id == self.instance_id:
                                        continue

                                    envelope_json = parsed.get("envelope")
                                    if envelope_json:
                                        envelope = EventEnvelope.model_validate_json(envelope_json)
                                        # Dispatch to local operators only (publish_redis=False to prevent loops)
                                        await self._dispatch_to_local_operators(envelope)
                                except Exception as parse_err:
                                    logger.debug(f"Error parsing cross-instance operator event: {parse_err}")
                    except asyncio.CancelledError:
                        raise
                    except Exception as loop_err:
                        logger.debug(f"Redis get_message error: {loop_err}")
                        await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"Redis pub/sub connection error ({exc}); retrying in 2s...")
                await asyncio.sleep(2.0)
            finally:
                try:
                    await pubsub.unsubscribe(OPERATOR_EVENT_CHANNEL)
                    await pubsub.close()
                except Exception:
                    pass

    @property
    def total_active_connections(self) -> int:
        return sum(len(conns) for conns in self.active_sessions.values())

    @property
    def total_operators(self) -> int:
        return len(self.operator_subscribers)


manager = ConnectionManager()
