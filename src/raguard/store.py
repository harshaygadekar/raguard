"""Token storage backends for RAGuard.

Defines the TokenStore protocol and provides InMemoryTokenStore as the
default implementation. For multi-process deployments (gunicorn workers,
Kubernetes pods), provide a custom TokenStore backed by Redis or similar.

Scaling guidance for InMemoryTokenStore:
  - Suitable for single-process deployments and up to ~50k concurrent sessions.
  - For multi-worker setups, use RedisTokenStore (``pip install "raguard[redis]"``).
  - Call ``clear_session()`` after each request cycle to bound memory usage.
"""

from __future__ import annotations

import threading
import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenStore(Protocol):
    """Protocol for canary token storage backends.

    All methods must be thread-safe. Implementations must handle concurrent
    access from multiple threads/coroutines without external locking.
    """

    def add_token(self, session_id: str, token: str) -> None:
        """Store a token for a session. Tokens accumulate per session."""
        ...

    def get_tokens(self, session_id: str) -> list[str]:
        """Return all active (non-expired) tokens for a session."""
        ...

    def has_token_in(self, session_id: str, text: str) -> bool:
        """Check if any active token for the session appears in text."""
        ...

    def clear_session(self, session_id: str) -> None:
        """Remove all tokens for a session."""
        ...


class InMemoryTokenStore:
    """Thread-safe in-memory token store with TTL and per-session limits.

    Suitable for single-process deployments. For multi-worker setups
    (gunicorn, Kubernetes), provide a custom TokenStore implementation
    backed by Redis or similar shared storage.

    Args:
        max_tokens_per_session: Maximum tokens kept per session. When
            exceeded, oldest tokens are evicted (FIFO). Default: 100.
        token_ttl_seconds: Seconds before a token expires. None means
            tokens never expire (must be cleaned up via clear_session).
        sweep_interval_seconds: If set, a background daemon thread runs
            every N seconds to evict expired sessions. Requires
            ``token_ttl_seconds`` to be set. Default: None (disabled).
        max_sessions: Maximum number of sessions. When exceeded, the
            oldest session (by earliest token timestamp) is evicted.
            Default: None (unlimited).
    """

    def __init__(
        self,
        max_tokens_per_session: int = 100,
        token_ttl_seconds: int | None = None,
        sweep_interval_seconds: float | None = None,
        max_sessions: int | None = None,
    ) -> None:
        self._lock = threading.Lock()
        # session_id -> [(monotonic_timestamp, token_value)]
        self._tokens: dict[str, list[tuple[float, str]]] = {}
        self._max_tokens = max_tokens_per_session
        self._ttl = token_ttl_seconds
        self._max_sessions = max_sessions
        self._sweep_thread: threading.Thread | None = None
        self._sweep_stop = threading.Event()

        if sweep_interval_seconds is not None and self._ttl is not None:
            self._start_sweep(sweep_interval_seconds)

    def _start_sweep(self, interval: float) -> None:
        """Start background daemon thread for periodic TTL eviction."""
        import weakref

        ref = weakref.ref(self)

        def _sweep_loop() -> None:
            while True:
                store = ref()
                if store is None:
                    break
                if store._sweep_stop.wait(timeout=interval):
                    break
                store._run_sweep()
                del store  # Release reference between iterations

        self._sweep_thread = threading.Thread(
            target=_sweep_loop, daemon=True, name="raguard-sweep"
        )
        self._sweep_thread.start()

    def _run_sweep(self) -> None:
        """Evict expired entries across all sessions."""
        if self._ttl is None:
            return
        cutoff = time.monotonic() - self._ttl
        with self._lock:
            expired_keys: list[str] = []
            for sid, entries in self._tokens.items():
                alive = [(t, tok) for t, tok in entries if t > cutoff]
                if alive:
                    self._tokens[sid] = alive
                else:
                    expired_keys.append(sid)
            for sid in expired_keys:
                del self._tokens[sid]

    def stop_sweep(self) -> None:
        """Stop the background sweep thread.

        Safe to call even if no sweep is running.
        """
        self._sweep_stop.set()
        if self._sweep_thread is not None:
            self._sweep_thread.join(timeout=2)
            self._sweep_thread = None

    def add_token(self, session_id: str, token: str) -> None:
        """Store a token for a session, evicting oldest if over limit."""
        with self._lock:
            if session_id not in self._tokens:
                self._tokens[session_id] = []
            self._tokens[session_id].append((time.monotonic(), token))
            # Evict oldest tokens if over per-session limit
            if len(self._tokens[session_id]) > self._max_tokens:
                self._tokens[session_id] = self._tokens[session_id][-self._max_tokens :]
            # Evict oldest session if over max-sessions limit
            if (
                self._max_sessions is not None
                and len(self._tokens) > self._max_sessions
            ):
                oldest_sid = min(
                    self._tokens,
                    key=lambda s: (
                        self._tokens[s][0][0] if self._tokens[s] else float("inf")
                    ),
                )
                if oldest_sid != session_id:
                    del self._tokens[oldest_sid]

    def get_tokens(self, session_id: str) -> list[str]:
        """Return active tokens, pruning expired entries if TTL is set."""
        with self._lock:
            entries = self._tokens.get(session_id, [])
            if self._ttl is not None:
                cutoff = time.monotonic() - self._ttl
                entries = [(t, tok) for t, tok in entries if t > cutoff]
                if entries:
                    self._tokens[session_id] = entries
                else:
                    self._tokens.pop(session_id, None)
            return [tok for _, tok in entries]

    def has_token_in(self, session_id: str, text: str) -> bool:
        """Check if any active token for the session appears in text."""
        tokens = self.get_tokens(session_id)
        return any(token in text for token in tokens)

    def clear_session(self, session_id: str) -> None:
        """Remove all tokens for a session."""
        with self._lock:
            self._tokens.pop(session_id, None)
