"""Concurrency tests for RAGuard core engine.

Verifies thread safety of InMemoryTokenStore and CanaryMiddleware under
concurrent access from multiple threads and asyncio tasks.
"""

import asyncio
import threading

from src.raguard.core import CanaryMiddleware


def test_concurrent_inject_and_scan_different_sessions():
    """10 threads each using different sessions — no crash, all isolated."""
    middleware = CanaryMiddleware()
    errors: list[str] = []
    barrier = threading.Barrier(10)

    def worker(thread_id: int) -> None:
        session_id = f"session_{thread_id}"
        barrier.wait()
        try:
            result = middleware.inject(
                [f"doc_{thread_id}_a", f"doc_{thread_id}_b"], session_id
            )
            assert isinstance(result, list)
            assert len(result) == 2
            # Token should be detectable
            for chunk in result:
                assert not middleware.is_safe(chunk, session_id)
        except Exception as exc:
            errors.append(f"Thread {thread_id}: {exc}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"Concurrency errors: {errors}"


def test_concurrent_inject_and_clear_same_session():
    """10 threads inject/clear on the SAME session — no crash."""
    middleware = CanaryMiddleware()
    errors: list[str] = []
    barrier = threading.Barrier(10)

    def worker(thread_id: int) -> None:
        barrier.wait()
        try:
            for _ in range(20):
                middleware.inject(["data"], "shared_session")
                middleware.is_safe("some response", "shared_session")
                middleware.clear_session("shared_session")
        except Exception as exc:
            errors.append(f"Thread {thread_id}: {exc}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"Concurrency errors: {errors}"


async def test_async_concurrent_inject_and_scan():
    """100 asyncio tasks concurrently calling inject_async and is_safe_async."""
    middleware = CanaryMiddleware()
    errors: list[str] = []

    async def worker(task_id: int) -> None:
        session_id = f"async_session_{task_id}"
        try:
            result = await middleware.inject_async([f"async_doc_{task_id}"], session_id)
            assert isinstance(result, list)
            for chunk in result:
                safe = await middleware.is_safe_async(chunk, session_id)
                assert not safe, f"Task {task_id}: expected unsafe but got safe"
        except Exception as exc:
            errors.append(f"Task {task_id}: {exc}")

    await asyncio.gather(*(worker(i) for i in range(100)))
    assert not errors, f"Async concurrency errors: {errors}"


def test_ttl_expiry_under_concurrent_access():
    """TTL expiry works correctly under concurrent access."""
    import time

    middleware = CanaryMiddleware(token_ttl_seconds=1)
    session_id = "ttl_test"
    errors: list[str] = []

    # Generate tokens
    middleware.inject(["data"], session_id)

    # Wait for TTL to expire
    time.sleep(1.1)

    barrier = threading.Barrier(5)

    def worker(thread_id: int) -> None:
        barrier.wait()
        try:
            # After TTL, is_safe should return True (tokens expired)
            assert middleware.is_safe("any response", session_id)
        except Exception as exc:
            errors.append(f"Thread {thread_id}: {exc}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"TTL concurrency errors: {errors}"


def test_session_isolation_under_concurrent_access():
    """Tokens from one session never bleed into another under concurrency."""
    middleware = CanaryMiddleware()
    session_count = 20
    barrier = threading.Barrier(session_count)
    results: dict[str, list[str]] = {}
    lock = threading.Lock()

    def worker(thread_id: int) -> None:
        session_id = f"iso_session_{thread_id}"
        barrier.wait()
        _ = middleware.inject([f"private_data_{thread_id}"], session_id)
        tokens = middleware._store.get_tokens(session_id)
        with lock:
            results[session_id] = tokens

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(session_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # Each session should have exactly 1 token
    for sid, tokens in results.items():
        assert len(tokens) == 1, f"{sid} has {len(tokens)} tokens"

    # No token should appear in another session's token list
    all_tokens = {sid: set(tokens) for sid, tokens in results.items()}
    for sid, tokens in all_tokens.items():
        for other_sid, other_tokens in all_tokens.items():
            if sid != other_sid:
                overlap = tokens & other_tokens
                assert not overlap, (
                    f"Token overlap between {sid} and {other_sid}: {overlap}"
                )
