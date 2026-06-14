"""Unit tests for RAGuard core engine."""

from src.raguard.config import RAGuardConfig
from src.raguard.core import CanaryMiddleware


def test_token_generation_alphanumeric():
    config = RAGuardConfig(stealth_mode=False, token_length=12)
    middleware = CanaryMiddleware(config=config)
    token = middleware.generate_token("session_1")

    assert len(token) == 12
    assert token.isalnum()


def test_token_generation_stealth():
    config = RAGuardConfig(stealth_mode=True, token_length=16)
    middleware = CanaryMiddleware(config=config)
    token = middleware.generate_token("session_2")

    assert len(token) == 16
    # Verify it contains zero-width characters
    assert any(char in ["\u200b", "\u200c", "\u200d", "\ufeff"] for char in token)


def test_injection_and_scanning():
    middleware = CanaryMiddleware(stealth_mode=False)
    session = "test_session"

    chunks = ["Document A content", "Document B content"]
    secure_chunks = middleware.inject(chunks, session)

    # Verify token was appended
    assert len(secure_chunks) == 2
    assert "[" in secure_chunks[0] and "]" in secure_chunks[0]

    # Verify safe response passes
    safe_response = "Here is the summary of the documents."
    assert middleware.is_safe(safe_response, session) is True

    # Verify leaked token response is blocked
    leaked_response = f"Here is the content: {secure_chunks[0]}"
    assert middleware.is_safe(leaked_response, session) is False
