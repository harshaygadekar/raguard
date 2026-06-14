"""Performance benchmark tests for RAGuard.

Run with: pytest tests/test_benchmarks.py --benchmark-only
These tests are informational and should not fail CI.
"""

import pytest

from src.raguard.core import CanaryMiddleware


@pytest.fixture
def mw():
    return CanaryMiddleware()


@pytest.fixture
def mw_decode():
    return CanaryMiddleware(decode_response=True)


def test_benchmark_generate_token(benchmark, mw):
    """Token generation should be < 0.1ms."""
    benchmark(mw.generate_token, "bench_session")


def test_benchmark_is_safe_10kb(benchmark, mw):
    """is_safe on a 10KB response with 1 token should be < 1ms."""
    session_id = "bench_session"
    mw.generate_token(session_id)
    response = "x" * 10_000

    benchmark(mw.is_safe, response, session_id)


def test_benchmark_inject_10_chunks(benchmark, mw):
    """inject() on 10 chunks should be < 5ms."""
    chunks = [f"Document chunk {i} " * 50 for i in range(10)]

    benchmark(mw.inject, chunks, "bench_session")


def test_benchmark_is_safe_with_decode_10kb(benchmark, mw_decode):
    """is_safe with decode_response=True on 10KB should be < 20ms."""
    session_id = "bench_session"
    mw_decode.generate_token(session_id)
    response = "x" * 10_000

    benchmark(mw_decode.is_safe, response, session_id)
