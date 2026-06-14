"""Shared test fixtures and helpers for RAGuard."""

import pytest

from src.raguard.core import CanaryMiddleware


@pytest.fixture
def middleware():
    """Fresh CanaryMiddleware in alphanumeric mode."""
    return CanaryMiddleware(stealth_mode=False)


@pytest.fixture
def stealth_middleware():
    """Fresh CanaryMiddleware in stealth (zero-width) mode."""
    return CanaryMiddleware(stealth_mode=True, token_length=16)


@pytest.fixture
def injected_docs(middleware):
    """Returns (middleware, secure_docs, session_id) with tokens injected."""
    session_id = "test_session"
    docs = middleware.inject(
        ["Confidential: Q3 revenue $5M", "Internal: API key sk-123abc"],
        session_id,
    )
    return middleware, docs, session_id


def extract_token(text: str) -> str:
    """Extract the most recently injected canary token from text.

    Tokens are appended in the format: '{original_text}\\n\\n[{TOKEN}]'.
    This extracts TOKEN without brackets by finding the last [...] pair.
    """
    return text.split("[")[-1].split("]")[0]
