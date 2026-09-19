"""SAMVED Core Redis Manager.

Provides resilient, asynchronous Redis utilities for:
1. Distributed session envelope caching across multi-instance serverless functions.
2. Cross-instance operator event fanout (Pub/Sub).
3. Distributed sliding-window rate limiting.
4. Graceful degradation when Redis is offline or unconfigured.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple
import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger("samved.core.redis")

# Global singleton client
_redis_client: Optional[aioredis.Redis] = None
_client_lock = asyncio.Lock()
_last_failure_time: float = 0.0
FAILURE_COOLDOWN_SECONDS: float = 10.0

# Key prefixes and channels
SESSION_KEY_PREFIX = "samved:telephony:session:"
PROVIDER_CALL_KEY_PREFIX = "samved:telephony:provider_call:"
OPERATOR_EVENT_CHANNEL = "samved:events:operator"
RATE_LIMIT_PREFIX = "samved:ratelimit:"

DEFAULT_SESSION_TTL_SECONDS = 3600  # 1 hour


async def get_redis_client() -> Optional[aioredis.Redis]:
    """Retrieves or initializes the async Redis client singleton.

    Returns None if REDIS_URL is not configured or connection fails.
    Caches connection failures for 10 seconds to avoid blocking when Redis is down.
    """
    global _redis_client, _last_failure_time
    settings = get_settings()

    if not settings.REDIS_URL:
        return None

    if _redis_client is not None:
        return _redis_client

    now = time.time()
    if (now - _last_failure_time) < FAILURE_COOLDOWN_SECONDS:
        return None

    async with _client_lock:
        if _redis_client is not None:
            return _redis_client

        if (time.time() - _last_failure_time) < FAILURE_COOLDOWN_SECONDS:
            return None

        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=0.5,
                health_check_interval=30,
            )
            # Verify connectivity with short timeout
            await asyncio.wait_for(client.ping(), timeout=0.5)
            _redis_client = client
            logger.info("Connected to Redis successfully.")
            return _redis_client
        except Exception as exc:
            _last_failure_time = time.time()
            logger.warning(f"Redis initialization failed ({exc}); falling back to in-memory mode.")
            return None


async def close_redis_client() -> None:
    """Closes active Redis connection pool on application shutdown."""
    global _redis_client
    async with _client_lock:
        if _redis_client is not None:
            try:
                await _redis_client.aclose()
                logger.info("Closed Redis connection pool.")
            except Exception as e:
                logger.debug(f"Error closing Redis client: {e}")
            finally:
                _redis_client = None


async def is_redis_available() -> bool:
    """Checks if Redis is currently configured and responsive."""
    client = await get_redis_client()
    if client is None:
        return False
    try:
        res = await asyncio.wait_for(client.ping(), timeout=1.0)
        return bool(res)
    except Exception:
        return False


# ============================================================================
# 1. Telephony Session Envelope Storage & Hydration
# ============================================================================

async def save_session_envelope(
    session_id: str,
    envelope: Dict[str, Any],
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
) -> bool:
    """Persists a complete session envelope in Redis with a bounded TTL.

    Ensures no raw secrets or tokens are stored.
    """
    client = await get_redis_client()
    if client is None:
        return False

    try:
        # Sanitize envelope: exclude any possible credentials
        sanitized = {
            k: v for k, v in envelope.items()
            if not any(secret_kw in k.lower() for secret_kw in ("secret", "token", "password", "key"))
        }
        payload = json.dumps(sanitized)
        key = f"{SESSION_KEY_PREFIX}{session_id}"

        pipe = client.pipeline()
        pipe.set(key, payload, ex=ttl_seconds)

        provider_call_id = sanitized.get("provider_call_id")
        if provider_call_id:
            lookup_key = f"{PROVIDER_CALL_KEY_PREFIX}{provider_call_id}"
            pipe.set(lookup_key, session_id, ex=ttl_seconds)

        await pipe.execute()
        logger.debug(f"Persisted session envelope to Redis for {session_id} (TTL: {ttl_seconds}s)")
        return True
    except Exception as exc:
        logger.warning(f"Failed to persist session envelope {session_id} to Redis: {exc}")
        return False


async def load_session_envelope(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves session envelope from Redis if available."""
    client = await get_redis_client()
    if client is None:
        return None

    try:
        key = f"{SESSION_KEY_PREFIX}{session_id}"
        raw = await client.get(key)
        if raw:
            return json.loads(raw)
        return None
    except Exception as exc:
        logger.warning(f"Failed to load session envelope {session_id} from Redis: {exc}")
        return None


async def get_session_id_by_provider_call(provider_call_id: str) -> Optional[str]:
    """Resolves provider call ID (e.g. Exotel CallSid) to SAMVED session_id."""
    client = await get_redis_client()
    if client is None:
        return None

    try:
        lookup_key = f"{PROVIDER_CALL_KEY_PREFIX}{provider_call_id}"
        return await client.get(lookup_key)
    except Exception as exc:
        logger.debug(f"Failed to lookup provider call {provider_call_id} in Redis: {exc}")
        return None


async def delete_session_envelope(
    session_id: str,
    provider_call_id: Optional[str] = None,
) -> bool:
    """Removes active session key from Redis upon call termination."""
    client = await get_redis_client()
    if client is None:
        return False

    try:
        key = f"{SESSION_KEY_PREFIX}{session_id}"
        keys_to_delete = [key]
        if provider_call_id:
            keys_to_delete.append(f"{PROVIDER_CALL_KEY_PREFIX}{provider_call_id}")
        await client.delete(*keys_to_delete)
        return True
    except Exception as exc:
        logger.debug(f"Failed to delete session envelope {session_id} from Redis: {exc}")
        return False


# ============================================================================
# 2. Distributed Operator Pub/Sub
# ============================================================================

async def publish_operator_event(
    envelope_json: str,
    origin_id: str,
    channel: str = OPERATOR_EVENT_CHANNEL,
) -> bool:
    """Publishes a serialized EventEnvelope to the Redis operator channel.

    Wrapped with a 50ms bounded timeout so telephony execution is NEVER blocked.
    """
    client = await get_redis_client()
    if client is None:
        return False

    try:
        message = json.dumps({
            "origin_id": origin_id,
            "envelope": envelope_json,
        })
        # Bounded timeout (50ms)
        await asyncio.wait_for(client.publish(channel, message), timeout=0.05)
        return True
    except asyncio.TimeoutError:
        logger.debug("Redis publish timed out (>50ms); dropped non-blocking operator event.")
        return False
    except Exception as exc:
        logger.debug(f"Redis publish failed: {exc}")
        return False


# ============================================================================
# 3. Distributed Rate Limiting (Sliding Window)
# ============================================================================

async def check_rate_limit_redis(
    key: str,
    limit: int = 60,
    window_seconds: int = 60,
    burst_allowance: int = 0,
) -> Optional[Tuple[bool, int, float]]:
    """Atomic sliding-window rate limit using Redis sorted sets.

    Returns:
        (allowed, current_count, retry_after_seconds)
        or None if Redis is unreachable (signaling caller to fallback to in-memory).
    """
    client = await get_redis_client()
    if client is None:
        return None

    redis_key = f"{RATE_LIMIT_PREFIX}{key}"
    block_key = f"{RATE_LIMIT_PREFIX}blocked:{key}"
    now = time.time()
    effective_limit = limit + burst_allowance

    try:
        # 1. Check if key is temporarily blocked
        blocked_until = await client.get(block_key)
        if blocked_until:
            rem = float(blocked_until) - now
            if rem > 0:
                return False, effective_limit, round(rem, 2)

        # 2. Atomic sliding window via pipeline
        cutoff = now - window_seconds
        pipe = client.pipeline()
        pipe.zremrangebyscore(redis_key, "-inf", cutoff)
        pipe.zcard(redis_key)
        results = await pipe.execute()

        current_count = results[1]

        if current_count >= effective_limit:
            # Check oldest entry to compute retry_after
            oldest_entries = await client.zrange(redis_key, 0, 0, withscores=True)
            if oldest_entries:
                oldest_ts = oldest_entries[0][1]
                retry_after = max(0.1, round((oldest_ts + window_seconds) - now, 2))
            else:
                retry_after = float(window_seconds)
            return False, current_count, retry_after

        # Quota available: add current timestamp with score = now and member = unique timestamp
        pipe = client.pipeline()
        pipe.zadd(redis_key, {f"{now}": now})
        pipe.expire(redis_key, window_seconds + 10)
        await pipe.execute()

        return True, current_count + 1, 0.0

    except Exception as exc:
        logger.debug(f"Redis rate limit check failed ({exc}); falling back to local limiter.")
        return None
