"""Redis-backed token store for RAGuard.

Enables multi-process and horizontally scaled deployments by storing
canary tokens in Redis instead of process-local memory.

Requires the ``redis`` package::

    pip install "raguard[redis]"
"""

from __future__ import annotations

import time
from typing import Any

try:
    import redis
except ImportError:
    redis = None  # type: ignore[assignment]


class RedisTokenStore:
    """Token store backed by Redis sorted sets.

    Each session's tokens are stored in a Redis sorted set keyed by
    ``{prefix}:{session_id}``. The score is the insertion timestamp
    (used for TTL eviction and FIFO ordering).

    Args:
        redis_client: A ``redis.Redis`` instance. If not provided, one is
            created from ``redis_url``.
        redis_url: Redis connection URL (e.g. ``redis://localhost:6379/0``).
            Ignored if ``redis_client`` is provided.
        max_tokens_per_session: Maximum tokens kept per session. Oldest
            tokens are evicted when exceeded. Default: 100.
        token_ttl_seconds: Seconds before tokens expire. ``None`` means
            tokens never expire. Default: ``None``.
        key_prefix: Redis key prefix to namespace RAGuard keys.
            Default: ``raguard:tokens``.
    """

    def __init__(
        self,
        redis_client: Any | None = None,
        redis_url: str = "redis://localhost:6379/0",
        max_tokens_per_session: int = 100,
        token_ttl_seconds: int | None = None,
        key_prefix: str = "raguard:tokens",
    ) -> None:
        r = redis
        if r is None:
            raise ImportError(
                "The RedisTokenStore requires the 'redis' package. "
                'Install it with: pip install "raguard[redis]"'
            )
        if redis_client is not None:
            self._redis: Any = redis_client
        else:
            self._redis = r.Redis.from_url(redis_url, decode_responses=True)

        self._max_tokens = max_tokens_per_session
        self._ttl = token_ttl_seconds
        self._prefix = key_prefix

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}:{session_id}"

    def add_token(self, session_id: str, token: str) -> None:
        """Store a token for a session using a sorted set (score = timestamp)."""
        key = self._key(session_id)
        now = time.time()

        pipe = self._redis.pipeline()
        pipe.zadd(key, {token: now})
        # Evict oldest tokens if over limit (keep only the newest N)
        pipe.zremrangebyrank(key, 0, -(self._max_tokens + 1))
        if self._ttl is not None:
            pipe.expire(key, self._ttl)
        pipe.execute()

    def get_tokens(self, session_id: str) -> list[str]:
        """Return active (non-expired) tokens for a session."""
        key = self._key(session_id)

        if self._ttl is not None:
            # Remove entries older than TTL
            cutoff = time.time() - self._ttl
            self._redis.zremrangebyscore(key, "-inf", cutoff)

        # Return all remaining tokens (oldest to newest)
        tokens = self._redis.zrange(key, 0, -1)
        return [t if isinstance(t, str) else t.decode("utf-8") for t in tokens]

    def has_token_in(self, session_id: str, text: str) -> bool:
        """Check if any active token for the session appears in text."""
        tokens = self.get_tokens(session_id)
        return any(token in text for token in tokens)

    def clear_session(self, session_id: str) -> None:
        """Remove all tokens for a session."""
        self._redis.delete(self._key(session_id))
