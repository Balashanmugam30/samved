"""Tests validating Vercel readiness, cross-instance Redis session hydration,

distributed operator pub/sub, rate limiting, and failure resilience.
"""

import asyncio
import json
import pytest
from starlette.testclient import TestClient

from app.core.config import get_settings
from app.core.telephony_state import CallState
from app.main import app
from app.realtime.connection_manager import ConnectionManager
from app.realtime.session_manager import RealtimeSessionManager, TelephonySession
from app.schemas.events import EventEnvelope, EventType
from app.security.rate_limit import RateLimiter, RateLimitResult


class MockAsyncRedis:
    """In-memory mock of redis.asyncio.Redis for deterministic testing."""

    def __init__(self):
        self.store = {}
        self.ttls = {}
        self.sorted_sets = {}
        self.channels = {}

    async def ping(self):
        return True

    async def aclose(self):
        pass

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        if ex:
            self.ttls[key] = ex
        return True

    async def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                count += 1
            if k in self.sorted_sets:
                del self.sorted_sets[k]
                count += 1
        return count

    def pipeline(self):
        return MockPipeline(self)

    async def publish(self, channel, message):
        subscribers = self.channels.get(channel, [])
        for q in subscribers:
            await q.put({"type": "message", "channel": channel, "data": message})
        return len(subscribers)

    def pubsub(self):
        return MockPubSub(self)

    # Sorted set methods for rate limiting
    async def zremrangebyscore(self, key, min_score, max_score):
        if key not in self.sorted_sets:
            return 0
        s = self.sorted_sets[key]
        before = len(s)
        self.sorted_sets[key] = {m: sc for m, sc in s.items() if sc > max_score}
        return before - len(self.sorted_sets[key])

    async def zcard(self, key):
        return len(self.sorted_sets.get(key, {}))

    async def zrange(self, key, start, stop, withscores=False):
        s = self.sorted_sets.get(key, {})
        sorted_items = sorted(s.items(), key=lambda x: x[1])
        slice_items = sorted_items[start : stop + 1 if stop != -1 else None]
        if withscores:
            return [(m, sc) for m, sc in slice_items]
        return [m for m, _ in slice_items]

    async def zadd(self, key, mapping):
        if key not in self.sorted_sets:
            self.sorted_sets[key] = {}
        self.sorted_sets[key].update(mapping)
        return len(mapping)

    async def expire(self, key, seconds):
        self.ttls[key] = seconds
        return True


class MockPipeline:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    def set(self, key, value, ex=None):
        self.commands.append(("set", (key, value, ex)))
        return self

    def zremrangebyscore(self, key, min_score, max_score):
        self.commands.append(("zremrangebyscore", (key, min_score, max_score)))
        return self

    def zcard(self, key):
        self.commands.append(("zcard", (key,)))
        return self

    def zadd(self, key, mapping):
        self.commands.append(("zadd", (key, mapping)))
        return self

    def expire(self, key, seconds):
        self.commands.append(("expire", (key, seconds)))
        return self

    async def execute(self):
        results = []
        for cmd, args in self.commands:
            method = getattr(self.redis, cmd)
            res = await method(*args)
            results.append(res)
        return results


class MockPubSub:
    def __init__(self, redis):
        self.redis = redis
        self.queue = asyncio.Queue()
        self.subscribed_channels = set()

    async def subscribe(self, channel):
        self.subscribed_channels.add(channel)
        self.redis.channels.setdefault(channel, []).append(self.queue)

    async def unsubscribe(self, channel):
        self.subscribed_channels.discard(channel)
        if channel in self.redis.channels and self.queue in self.redis.channels[channel]:
            self.redis.channels[channel].remove(self.queue)

    async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def close(self):
        for ch in list(self.subscribed_channels):
            await self.unsubscribe(ch)


@pytest.fixture
def mock_redis(monkeypatch):
    """Provides a fresh MockAsyncRedis instance patched into app.core.redis."""
    redis_instance = MockAsyncRedis()

    async def mock_get_client():
        return redis_instance

    monkeypatch.setattr("app.core.redis.get_redis_client", mock_get_client)
    monkeypatch.setattr("app.core.redis._redis_client", redis_instance)
    return redis_instance


# ============================================================================
# TEST A: HTTP resolver on Instance 1 -> WebSocket on Instance 2
# ============================================================================

@pytest.mark.asyncio
async def test_a_http_resolver_and_ws_on_different_instances(mock_redis):
    """Simulates Instance 1 creating a session and saving it to Redis,

    then Instance 2 successfully hydrating it from Redis.
    """
    from app.core.redis import save_session_envelope, load_session_envelope

    # Instance 1: provisions session
    inst1_manager = RealtimeSessionManager()
    session_id = "SESS-cross-inst-01"
    call_id = "CALL-cross-inst-01"
    provider_call_id = "EXO-CALL-12345"
    caller_number = "+919876543210"

    sess1 = await inst1_manager.create_session(
        session_id=session_id,
        call_id=call_id,
        provider_call_id=provider_call_id,
        caller_number=caller_number,
        provider="exotel",
        attach_ai=False,
    )
    # Save envelope to Redis
    envelope = {
        "session_id": session_id,
        "call_id": call_id,
        "provider_call_id": provider_call_id,
        "caller_number": caller_number,
        "masked_caller_number": sess1.masked_caller_number,
        "provider": "exotel",
        "created_at": sess1.created_at,
        "mode": "DEV",
        "state": "CONNECTING",
        "primary_language": "ta-IN",
    }
    await save_session_envelope(session_id, envelope)

    # Instance 2: completely separate session manager with empty local memory
    inst2_manager = RealtimeSessionManager()
    assert (await inst2_manager.get_session(session_id)) is None

    # Instance 2 hydrates from Redis
    hydrated = await inst2_manager.hydrate_session_from_redis(session_id)
    assert hydrated is not None
    assert hydrated.session_id == session_id
    assert hydrated.call_id == call_id
    assert hydrated.provider_call_id == provider_call_id
    assert hydrated.masked_caller_number == sess1.masked_caller_number
    assert hydrated.state_machine.current_state == CallState.CONNECTING

    # Now local lookup succeeds on Instance 2
    assert (await inst2_manager.get_session(session_id)) is not None


# ============================================================================
# TEST B: Local session absent, Redis session present -> WS succeeds
# ============================================================================

def test_b_local_session_absent_redis_session_present(mock_redis, monkeypatch):
    """WebSocket connection succeeds when local memory is empty but Redis contains envelope."""
    from app.core.redis import save_session_envelope
    from app.realtime.session_manager import telephony_session_manager

    session_id = "SESS-redis-only-99"
    envelope = {
        "session_id": session_id,
        "call_id": "CALL-redis-only-99",
        "provider_call_id": "EXO-99999",
        "caller_number": "+919876543210",
        "masked_caller_number": "+91******3210",
        "provider": "exotel",
        "created_at": "2026-09-19T06:00:00Z",
        "mode": "DEV",
        "state": "CONNECTING",
        "primary_language": "ta-IN",
    }
    # Persist in mock Redis
    asyncio.run(save_session_envelope(session_id, envelope))

    # Ensure local memory does NOT have it
    telephony_session_manager._sessions.pop(session_id, None)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/telephony/exotel/{session_id}") as ws:
        # Handshake: Exotel sends connected event
        ws.send_text(json.dumps({"event": "connected"}))
        # Send start event
        ws.send_text(json.dumps({
            "event": "start",
            "start": {"streamSid": "stream-test-b"},
        }))
        # Send stop event
        ws.send_text(json.dumps({"event": "stop"}))


# ============================================================================
# TEST C: Redis session absent -> safe deterministic failure (4004)
# ============================================================================

def test_c_redis_session_absent_safe_deterministic_failure(mock_redis):
    """WebSocket connection is rejected with 4004 when session is absent everywhere."""
    from app.realtime.session_manager import telephony_session_manager

    session_id = "SESS-ghost-session"
    telephony_session_manager._sessions.pop(session_id, None)

    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/telephony/exotel/{session_id}") as ws:
            ws.receive_text()


# ============================================================================
# TEST D: Two operator clients on separate simulated instances
# ============================================================================

@pytest.mark.asyncio
async def test_d_two_operator_clients_on_separate_instances(mock_redis):
    """Validates that events published by Instance A are delivered to Instance B's operator subscribers."""
    inst_a = ConnectionManager()
    inst_b = ConnectionManager()

    # Create mock WebSockets for each instance
    received_on_b = []

    class MockWS:
        def __init__(self, target_list):
            self.target_list = target_list

        async def send_text(self, text):
            self.target_list.append(json.loads(text))

    ws_b = MockWS(received_on_b)
    inst_b.register_operator(ws_b, call_id=None)

    # Start Redis listener on Instance B
    inst_b.start_redis_listener()
    await asyncio.sleep(0.05)  # Allow subscription to register

    # Instance A broadcasts an event
    test_envelope = EventEnvelope(
        event_type=EventType.SAFETY_STATE_UPDATED,
        session_id="SESS-test-d",
        call_id="CALL-test-d",
        payload={"state": "ELEVATED", "reason": "test_signal"},
    )
    await inst_a.broadcast_to_operators(test_envelope, publish_redis=True)

    # Give event loop a moment to propagate through mock Redis pub/sub
    await asyncio.sleep(0.1)

    assert len(received_on_b) >= 1
    assert received_on_b[0]["event_type"] == EventType.SAFETY_STATE_UPDATED.value
    assert received_on_b[0]["call_id"] == "CALL-test-d"

    await inst_b.stop_redis_listener()


# ============================================================================
# TEST E: Redis unavailable -> safe local fallback
# ============================================================================

@pytest.mark.asyncio
async def test_e_redis_unavailable_telephony_safe_degradation(monkeypatch):
    """When Redis is completely unreachable, telephony session creation and broadcasting

    continue safely in local memory without raising errors.
    """
    async def mock_none_client():
        return None

    monkeypatch.setattr("app.core.redis.get_redis_client", mock_none_client)

    mgr = RealtimeSessionManager()
    session = await mgr.create_session(
        session_id="SESS-fallback-01",
        call_id="CALL-fallback-01",
        provider_call_id="EXO-FALLBACK",
        caller_number="+919876543210",
        attach_ai=False,
    )
    assert session is not None
    assert session.session_id == "SESS-fallback-01"

    # Broadcast event should not fail even if Redis is unavailable
    conn_mgr = ConnectionManager()
    test_env = EventEnvelope(
        event_type=EventType.CALL_STARTED,
        session_id="SESS-fallback-01",
        call_id="CALL-fallback-01",
        payload={"status": "testing_offline_redis"},
    )
    # Must not raise an exception
    await conn_mgr.broadcast_to_operators(test_env, publish_redis=True)


# ============================================================================
# TEST F: Session TTL and cleanup
# ============================================================================

@pytest.mark.asyncio
async def test_f_session_cleanup(mock_redis):
    """Validates session envelope deletion from Redis upon call termination."""
    from app.core.redis import save_session_envelope, load_session_envelope, delete_session_envelope

    session_id = "SESS-cleanup-test"
    provider_call_id = "EXO-CLEANUP"
    envelope = {"session_id": session_id, "provider_call_id": provider_call_id}

    await save_session_envelope(session_id, envelope)
    assert (await load_session_envelope(session_id)) is not None

    # Delete envelope
    deleted = await delete_session_envelope(session_id, provider_call_id)
    assert deleted is True
    assert (await load_session_envelope(session_id)) is None


# ============================================================================
# TEST G: Distributed rate limiting
# ============================================================================

@pytest.mark.asyncio
async def test_g_distributed_rate_limiting(mock_redis):
    """Validates sliding-window rate limiting with Redis."""
    limiter = RateLimiter()

    # Under quota
    res1 = await limiter.check_async("user-test-key", limit=2, window_seconds=60)
    assert res1.allowed is True
    assert res1.current_count == 1

    res2 = await limiter.check_async("user-test-key", limit=2, window_seconds=60)
    assert res2.allowed is True
    assert res2.current_count == 2

    # Quota exceeded
    res3 = await limiter.check_async("user-test-key", limit=2, window_seconds=60)
    assert res3.allowed is False
    assert res3.retry_after_seconds > 0
