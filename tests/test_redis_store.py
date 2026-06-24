"""Tests for RedisTokenStore.

Uses fakeredis to simulate Redis without requiring a running Redis server.
"""

import time

import fakeredis
import pytest

from src.raguard.redis_store import RedisTokenStore


@pytest.fixture
def redis_client():
    """Create a fakeredis client for testing."""
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def store(redis_client):
    """Create a RedisTokenStore backed by fakeredis."""
    return RedisTokenStore(
        redis_client=redis_client,
        max_tokens_per_session=100,
        token_ttl_seconds=None,
    )


class TestRedisTokenStoreBasic:
    """Core protocol compliance: add, get, has_token_in, clear."""

    def test_add_and_get_tokens(self, store):
        store.add_token("s1", "tok_a")
        store.add_token("s1", "tok_b")
        tokens = store.get_tokens("s1")
        assert "tok_a" in tokens
        assert "tok_b" in tokens

    def test_get_tokens_empty_session(self, store):
        assert store.get_tokens("nonexistent") == []

    def test_has_token_in_positive(self, store):
        store.add_token("s1", "secret123")
        assert store.has_token_in("s1", "The secret123 leaked")

    def test_has_token_in_negative(self, store):
        store.add_token("s1", "secret123")
        assert not store.has_token_in("s1", "Clean response")

    def test_clear_session(self, store):
        store.add_token("s1", "tok_a")
        store.clear_session("s1")
        assert store.get_tokens("s1") == []

    def test_sessions_are_isolated(self, store):
        store.add_token("s1", "tok_a")
        store.add_token("s2", "tok_b")
        assert store.get_tokens("s1") == ["tok_a"]
        assert store.get_tokens("s2") == ["tok_b"]


class TestRedisTokenStoreFIFO:
    """FIFO eviction when max_tokens_per_session is exceeded."""

    def test_evicts_oldest_tokens(self, redis_client):
        store = RedisTokenStore(
            redis_client=redis_client,
            max_tokens_per_session=3,
        )
        for i in range(5):
            store.add_token("s1", f"tok_{i}")

        tokens = store.get_tokens("s1")
        assert len(tokens) == 3
        # Oldest (tok_0, tok_1) evicted; newest remain
        assert "tok_2" in tokens
        assert "tok_3" in tokens
        assert "tok_4" in tokens
        assert "tok_0" not in tokens
        assert "tok_1" not in tokens


class TestRedisTokenStoreTTL:
    """TTL-based expiration of tokens."""

    def test_ttl_expires_tokens(self, redis_client):
        store = RedisTokenStore(
            redis_client=redis_client,
            token_ttl_seconds=1,
        )
        store.add_token("s1", "tok_old")
        time.sleep(1.1)
        assert store.get_tokens("s1") == []

    def test_fresh_tokens_survive_ttl(self, redis_client):
        store = RedisTokenStore(
            redis_client=redis_client,
            token_ttl_seconds=5,
        )
        store.add_token("s1", "tok_fresh")
        tokens = store.get_tokens("s1")
        assert "tok_fresh" in tokens


class TestRedisTokenStoreIntegration:
    """Integration with CanaryMiddleware."""

    def test_middleware_with_redis_store(self, redis_client):
        from src.raguard.core import CanaryMiddleware

        store = RedisTokenStore(redis_client=redis_client)
        mw = CanaryMiddleware(store=store)

        mw.generate_token("s1")
        injected = mw.inject("sensitive doc", "s1")

        # Token should be detected in leaked response
        assert not mw.is_safe(injected, "s1")

        # Clean response should pass
        mw.generate_token("s2")
        assert mw.is_safe("Safe summary", "s2")

    def test_clear_session_via_middleware(self, redis_client):
        from src.raguard.core import CanaryMiddleware

        store = RedisTokenStore(redis_client=redis_client)
        mw = CanaryMiddleware(store=store)

        token = mw.generate_token("s1")
        mw.clear_session("s1")
        # After clearing, the token should not be detected
        assert mw.is_safe(f"Leaked: {token}", "s1")


class TestRedisTokenStoreImportError:
    """RedisTokenStore raises clear error when redis is not installed."""

    def test_import_error_message(self, monkeypatch):
        import src.raguard.redis_store as mod

        monkeypatch.setattr(mod, "redis", None)
        with pytest.raises(ImportError, match="raguard-security\\[redis\\]"):
            RedisTokenStore()
