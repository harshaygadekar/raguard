"""Unit tests for RAGuard webhook functionality."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.raguard.config import RAGuardConfig
from src.raguard.core import CanaryMiddleware


def test_webhook_fires_on_detection():
    """_trigger_alert calls urllib.request.urlopen when alert_webhook_url is set."""
    config = RAGuardConfig(alert_webhook_url="http://example.com/webhook")
    middleware = CanaryMiddleware(config=config)

    # Generate token for session
    token = middleware.generate_token("test_session")

    # Create response with leaked token
    leaked_response = f"Here is the secret: {token}"

    with patch("src.raguard.core.urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Trigger detection
        result = middleware.is_safe(leaked_response, "test_session")

        assert result is False
        assert mock_urlopen.called


def test_webhook_not_fired_when_safe():
    """_trigger_alert not called when is_safe returns True."""
    config = RAGuardConfig(alert_webhook_url="http://example.com/webhook")
    middleware = CanaryMiddleware(config=config)

    middleware.generate_token("test_session")
    safe_response = "This is a clean response without the token"

    with patch("src.raguard.core.urllib.request.urlopen") as mock_urlopen:
        result = middleware.is_safe(safe_response, "test_session")

        assert result is True
        assert not mock_urlopen.called


def test_webhook_payload_structure():
    """JSON payload contains event, session_id, timestamp, response_snippet."""
    config = RAGuardConfig(alert_webhook_url="http://example.com/webhook")
    middleware = CanaryMiddleware(config=config)

    token = middleware.generate_token("session_123")
    leaked_response = f"Leaked: {token}"

    with patch("src.raguard.core.urllib.request.urlopen") as mock_urlopen:
        middleware.is_safe(leaked_response, "session_123")

        # Extract the request object passed to urlopen
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        payload = json.loads(request_obj.data.decode("utf-8"))

        assert payload["event"] == "canary_token_detected"
        assert payload["session_id"] == "session_123"
        assert "timestamp" in payload
        assert "response_snippet" in payload


def test_webhook_failure_does_not_raise():
    """urllib.error.URLError is caught and logged, not propagated."""
    import urllib.error

    config = RAGuardConfig(alert_webhook_url="http://example.com/webhook")
    middleware = CanaryMiddleware(config=config)

    token = middleware.generate_token("test_session")
    leaked_response = f"Leaked: {token}"

    with patch("src.raguard.core.urllib.request.urlopen") as mock_urlopen:
        # Simulate network failure
        mock_urlopen.side_effect = urllib.error.URLError("Connection failed")

        # Should not raise exception
        result = middleware.is_safe(leaked_response, "test_session")

        assert result is False


def test_webhook_no_url_skips():
    """No HTTP call when alert_webhook_url is None."""
    config = RAGuardConfig(alert_webhook_url=None)
    middleware = CanaryMiddleware(config=config)

    token = middleware.generate_token("test_session")
    leaked_response = f"Leaked: {token}"

    with patch("src.raguard.core.urllib.request.urlopen") as mock_urlopen:
        result = middleware.is_safe(leaked_response, "test_session")

        assert result is False
        assert not mock_urlopen.called


def test_webhook_response_truncated():
    """response_snippet is max 500 chars when include_response_snippet=True."""
    config = RAGuardConfig(
        alert_webhook_url="http://example.com/webhook",
        include_response_snippet=True,
    )
    middleware = CanaryMiddleware(config=config)

    token = middleware.generate_token("test_session")
    # Create a very long response
    long_response = f"Leaked: {token} " + "x" * 1000

    with patch("src.raguard.core.urllib.request.urlopen") as mock_urlopen:
        middleware.is_safe(long_response, "test_session")

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        payload = json.loads(request_obj.data.decode("utf-8"))

        assert len(payload["response_snippet"]) <= 500


@pytest.mark.asyncio
async def test_async_webhook_fires():
    """is_safe_async triggers _trigger_alert_async."""
    config = RAGuardConfig(alert_webhook_url="http://example.com/webhook")
    middleware = CanaryMiddleware(config=config)

    token = middleware.generate_token("async_session")
    leaked_response = f"Async leaked: {token}"

    with patch("src.raguard.core.urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = await middleware.is_safe_async(leaked_response, "async_session")

        assert result is False
        assert mock_urlopen.called


@pytest.mark.asyncio
async def test_async_webhook_non_blocking():
    """asyncio.to_thread is used for webhook delivery."""
    config = RAGuardConfig(alert_webhook_url="http://example.com/webhook")
    middleware = CanaryMiddleware(config=config)

    token = middleware.generate_token("async_session")
    leaked_response = f"Async leaked: {token}"

    with patch("src.raguard.core.asyncio.to_thread") as mock_to_thread:
        with patch("src.raguard.core.urllib.request.urlopen"):
            await middleware.is_safe_async(leaked_response, "async_session")

            assert mock_to_thread.called
