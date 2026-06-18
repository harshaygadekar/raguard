"""Tests for production hardening features added during readiness review.

Covers: SSRF protection, circuit breaker, metrics, graceful degradation,
response snippet opt-in, encoding bypass detection, injection position,
stealth mode validation, session ID generation.
"""

import json
import time
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.raguard.config import RAGuardConfig
from src.raguard.core import CanaryMiddleware

# --- SSRF Protection ---


class TestSSRFProtection:
    """Webhook SSRF protection blocks private/loopback/non-HTTP URLs."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/webhook",
            "http://10.0.0.1/webhook",
            "http://172.16.0.1/webhook",
            "http://192.168.1.1/webhook",
            "http://169.254.169.254/latest/meta-data/",  # AWS IMDS
        ],
    )
    def test_private_ip_blocked_at_runtime(self, url):
        """Private/loopback IP URLs are blocked before HTTP call is made."""
        config = RAGuardConfig(alert_webhook_url=url)
        middleware = CanaryMiddleware(config=config)
        token = middleware.generate_token("ssrf_test")
        leaked = f"Leaked: {token}"

        with patch("src.raguard.core.urllib.request.urlopen") as mock:
            middleware.is_safe(leaked, "ssrf_test")
            assert not mock.called, f"HTTP call made to SSRF URL: {url}"

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "ftp://internal.server/data",
            "gopher://internal.server/",
        ],
    )
    def test_non_http_schemes_rejected_at_config(self, url):
        """Non-HTTP schemes are rejected at config creation time."""
        with pytest.raises(ValidationError, match="http:// or https://"):
            RAGuardConfig(alert_webhook_url=url)

    def test_valid_https_url_allowed(self):
        """Valid public HTTPS URLs are allowed."""
        config = RAGuardConfig(alert_webhook_url="https://hooks.slack.com/services/xxx")
        middleware = CanaryMiddleware(config=config)
        token = middleware.generate_token("valid_test")
        leaked = f"Leaked: {token}"

        with patch("src.raguard.core.urllib.request.urlopen") as mock:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock.return_value.__enter__.return_value = mock_resp
            middleware.is_safe(leaked, "valid_test")
            assert mock.called

    def test_dns_hostname_allowed(self):
        """DNS hostnames (non-IP) are allowed through."""
        config = RAGuardConfig(alert_webhook_url="https://my-webhook.example.com/alert")
        middleware = CanaryMiddleware(config=config)
        assert middleware._is_safe_webhook_target(
            "https://my-webhook.example.com/alert"
        )


# --- Circuit Breaker ---


class TestCircuitBreaker:
    """Webhook circuit breaker opens after N failures, resets after timeout."""

    def test_circuit_opens_after_threshold(self):
        """After 5 consecutive failures, webhook calls are skipped."""
        config = RAGuardConfig(
            alert_webhook_url="http://example.com/webhook",
            webhook_circuit_breaker_threshold=3,
            webhook_circuit_breaker_reset_seconds=60,
        )
        middleware = CanaryMiddleware(config=config)

        with patch("src.raguard.core.urllib.request.urlopen") as mock:
            mock.side_effect = urllib.error.URLError("fail")

            # Trigger 3 failures to open circuit
            for i in range(3):
                token = middleware.generate_token(f"cb_{i}")
                middleware.is_safe(f"Leaked: {token}", f"cb_{i}")

            assert mock.call_count == 3

            # Now circuit is open — 4th call should NOT make HTTP request
            token = middleware.generate_token("cb_4")
            middleware.is_safe(f"Leaked: {token}", "cb_4")
            assert mock.call_count == 3  # No additional call

    def test_circuit_resets_after_timeout(self):
        """Circuit closes after reset_seconds elapses."""
        config = RAGuardConfig(
            alert_webhook_url="http://example.com/webhook",
            webhook_circuit_breaker_threshold=2,
            webhook_circuit_breaker_reset_seconds=1,
        )
        middleware = CanaryMiddleware(config=config)

        with patch("src.raguard.core.urllib.request.urlopen") as mock:
            mock.side_effect = urllib.error.URLError("fail")

            # Open the circuit
            for i in range(2):
                token = middleware.generate_token(f"cb_{i}")
                middleware.is_safe(f"Leaked: {token}", f"cb_{i}")
            assert mock.call_count == 2

            # Wait for reset
            time.sleep(1.1)

            # Circuit should be half-open, allowing retry
            mock.side_effect = None
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock.return_value.__enter__.return_value = mock_resp

            token = middleware.generate_token("cb_reset")
            middleware.is_safe(f"Leaked: {token}", "cb_reset")
            assert mock.call_count == 3  # Retried


# --- Metrics ---


class TestMetrics:
    """RAGuardMetrics counters increment correctly."""

    def test_tokens_generated_counter(self):
        mw = CanaryMiddleware()
        mw.generate_token("s1")
        mw.generate_token("s2")
        assert mw.metrics.tokens_generated == 2

    def test_scan_safe_counter(self):
        mw = CanaryMiddleware()
        mw.generate_token("s1")
        mw.is_safe("clean response", "s1")
        assert mw.metrics.scans_safe == 1
        assert mw.metrics.scans_total == 1

    def test_scan_blocked_counter(self):
        mw = CanaryMiddleware()
        token = mw.generate_token("s1")
        mw.is_safe(f"Leaked: {token}", "s1")
        assert mw.metrics.scans_blocked == 1
        assert mw.metrics.tokens_detected == 1
        assert mw.metrics.scans_total == 1

    def test_webhook_counters(self):
        config = RAGuardConfig(
            alert_webhook_url="http://example.com/webhook",
        )
        mw = CanaryMiddleware(config=config)
        token = mw.generate_token("s1")

        with patch("src.raguard.core.urllib.request.urlopen") as mock:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock.return_value.__enter__.return_value = mock_resp
            mw.is_safe(f"Leaked: {token}", "s1")

        assert mw.metrics.webhook_successes == 1

    def test_webhook_failure_counter(self):
        config = RAGuardConfig(
            alert_webhook_url="http://example.com/webhook",
        )
        mw = CanaryMiddleware(config=config)
        token = mw.generate_token("s1")

        with patch("src.raguard.core.urllib.request.urlopen") as mock:
            mock.side_effect = urllib.error.URLError("fail")
            mw.is_safe(f"Leaked: {token}", "s1")

        assert mw.metrics.webhook_failures == 1

    def test_metrics_snapshot_is_independent(self):
        """Snapshot returns a copy, not a reference."""
        mw = CanaryMiddleware()
        snap1 = mw.metrics
        mw.generate_token("s1")
        snap2 = mw.metrics
        assert snap1.tokens_generated == 0
        assert snap2.tokens_generated == 1


# --- Graceful Degradation ---


class TestGracefulDegradation:
    """fail_open mode returns safe defaults when store fails."""

    def _make_failing_store(self):
        """Create a store that raises on all operations."""

        class FailingStore:
            def add_token(self, session_id, token):
                raise RuntimeError("store down")

            def get_tokens(self, session_id):
                raise RuntimeError("store down")

            def has_token_in(self, session_id, text):
                raise RuntimeError("store down")

            def clear_session(self, session_id):
                raise RuntimeError("store down")

        return FailingStore()

    def test_inject_fail_open_returns_unmodified(self):
        """With fail_open=True, inject returns chunks unmodified on store error."""
        mw = CanaryMiddleware(
            config=RAGuardConfig(fail_open=True),
            store=self._make_failing_store(),
        )
        chunks = ["doc1", "doc2"]
        result = mw.inject(chunks, "s1")
        assert result == chunks

    def test_is_safe_fail_open_returns_true(self):
        """With fail_open=True, is_safe returns True on store error."""
        mw = CanaryMiddleware(
            config=RAGuardConfig(fail_open=True),
            store=self._make_failing_store(),
        )
        assert mw.is_safe("any response", "s1") is True

    def test_fail_closed_propagates_exception(self):
        """With fail_open=False, store errors propagate."""
        mw = CanaryMiddleware(
            config=RAGuardConfig(fail_open=False),
            store=self._make_failing_store(),
        )
        with pytest.raises(RuntimeError, match="store down"):
            mw.inject(["doc"], "s1")

    def test_fail_closed_is_safe_propagates(self):
        """With fail_open=False, is_safe store errors propagate."""
        mw = CanaryMiddleware(
            config=RAGuardConfig(fail_open=False),
            store=self._make_failing_store(),
        )
        with pytest.raises(RuntimeError, match="store down"):
            mw.is_safe("response", "s1")


# --- Response Snippet ---


class TestResponseSnippet:
    """include_response_snippet controls webhook payload content."""

    def test_redacted_by_default(self):
        config = RAGuardConfig(alert_webhook_url="http://example.com/webhook")
        mw = CanaryMiddleware(config=config)
        token = mw.generate_token("s1")

        with patch("src.raguard.core.urllib.request.urlopen") as mock:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock.return_value.__enter__.return_value = mock_resp
            mw.is_safe(f"Leaked: {token}", "s1")

            req = mock.call_args[0][0]
            payload = json.loads(req.data)
            assert payload["response_snippet"] == "[redacted]"

    def test_included_when_opted_in(self):
        config = RAGuardConfig(
            alert_webhook_url="http://example.com/webhook",
            include_response_snippet=True,
        )
        mw = CanaryMiddleware(config=config)
        token = mw.generate_token("s1")
        leaked = f"Leaked: {token}"

        with patch("src.raguard.core.urllib.request.urlopen") as mock:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock.return_value.__enter__.return_value = mock_resp
            mw.is_safe(leaked, "s1")

            req = mock.call_args[0][0]
            payload = json.loads(req.data)
            assert "Leaked:" in payload["response_snippet"]


# --- Encoding Bypass Detection ---


class TestEncodingBypassDetection:
    """decode_response detects encoding-bypassed tokens."""

    def test_base64_detected_with_decode(self):
        import base64

        mw = CanaryMiddleware(decode_response=True)
        token = mw.generate_token("s1")
        encoded = base64.b64encode(token.encode()).decode()
        assert not mw.is_safe(encoded, "s1")

    def test_base64_missed_without_decode(self):
        import base64

        mw = CanaryMiddleware(decode_response=False)
        token = mw.generate_token("s1")
        encoded = base64.b64encode(token.encode()).decode()
        assert mw.is_safe(encoded, "s1")

    def test_rot13_detected_with_decode(self):
        import codecs

        mw = CanaryMiddleware(decode_response=True)
        token = mw.generate_token("s1")
        encoded = codecs.encode(token, "rot_13")
        assert not mw.is_safe(encoded, "s1")

    def test_reversed_detected_with_decode(self):
        mw = CanaryMiddleware(decode_response=True)
        token = mw.generate_token("s1")
        reversed_token = token[::-1]
        assert not mw.is_safe(reversed_token, "s1")

    def test_character_splitting_detected_with_decode(self):
        mw = CanaryMiddleware(decode_response=True)
        token = mw.generate_token("s1")
        split_token = " ".join(token)  # "a b c d ..."
        assert not mw.is_safe(split_token, "s1")


# --- Injection Position ---


class TestInjectionPosition:
    """Token injection position is configurable."""

    def test_append_default(self):
        mw = CanaryMiddleware()
        result = mw.inject("doc", "s1")
        assert result.startswith("doc")

    def test_prepend(self):
        mw = CanaryMiddleware(injection_position="prepend")
        result = mw.inject("doc", "s1")
        assert result.endswith("doc")

    def test_both_positions_detectable(self):
        for pos in ("append", "prepend"):
            mw = CanaryMiddleware(injection_position=pos)
            result = mw.inject("doc", "s1")
            assert not mw.is_safe(result, "s1")


# --- Token Wrapper ---


class TestTokenWrapper:
    """Custom token_wrapper format is applied."""

    def test_custom_wrapper(self):
        mw = CanaryMiddleware(token_wrapper="<<{token}>>")
        result = mw.inject("doc", "s1")
        assert "<<" in result and ">>" in result

    def test_default_wrapper(self):
        mw = CanaryMiddleware()
        result = mw.inject("doc", "s1")
        assert "\n\n[" in result and "]" in result


# --- Stealth Mode Validation ---


class TestStealthValidation:
    """Stealth mode enforces minimum token_length=16."""

    def test_stealth_rejects_short_token(self):
        with pytest.raises(ValidationError, match="token_length >= 16"):
            RAGuardConfig(stealth_mode=True, token_length=8)

    def test_stealth_accepts_16(self):
        config = RAGuardConfig(stealth_mode=True, token_length=16)
        assert config.token_length == 16

    def test_non_stealth_allows_8(self):
        config = RAGuardConfig(stealth_mode=False, token_length=8)
        assert config.token_length == 8


# --- Config Validation ---


class TestConfigValidation:
    """Configuration validation at startup."""

    def test_invalid_webhook_scheme_rejected(self):
        with pytest.raises(ValidationError, match="http:// or https://"):
            RAGuardConfig(alert_webhook_url="ftp://evil.com/hook")

    def test_valid_webhook_accepted(self):
        config = RAGuardConfig(alert_webhook_url="https://hooks.slack.com/x")
        assert config.alert_webhook_url == "https://hooks.slack.com/x"

    def test_invalid_injection_position_rejected(self):
        with pytest.raises(ValidationError, match="append.*prepend"):
            RAGuardConfig(injection_position="middle")


# --- TokenStore ---


class TestTokenStore:
    """InMemoryTokenStore TTL and eviction behavior."""

    def test_ttl_expiry(self):
        mw = CanaryMiddleware(token_ttl_seconds=1)
        token = mw.generate_token("s1")
        assert not mw.is_safe(f"Leaked: {token}", "s1")

        time.sleep(1.1)
        # After TTL, token expired — response should be safe
        assert mw.is_safe(f"Leaked: {token}", "s1")

    def test_max_tokens_eviction(self):
        mw = CanaryMiddleware(max_tokens_per_session=3)
        tokens = [mw.generate_token("s1") for _ in range(5)]
        # Only last 3 should remain
        stored = mw._store.get_tokens("s1")
        assert len(stored) == 3
        assert stored == tokens[-3:]

    def test_clear_session(self):
        mw = CanaryMiddleware()
        token = mw.generate_token("s1")
        mw.clear_session("s1")
        assert mw.is_safe(f"Leaked: {token}", "s1")


class TestSweepThread:
    """Background sweep evicts expired sessions proactively."""

    def test_sweep_evicts_expired_sessions(self):
        from src.raguard.store import InMemoryTokenStore

        store = InMemoryTokenStore(
            token_ttl_seconds=1,
            sweep_interval_seconds=0.5,
        )
        try:
            store.add_token("s1", "tok_a")
            assert store.get_tokens("s1") == ["tok_a"]

            # Wait for TTL + sweep interval
            time.sleep(2.0)

            # Session should be evicted by sweep, not by get_tokens
            with store._lock:
                assert "s1" not in store._tokens
        finally:
            store.stop_sweep()

    def test_sweep_does_not_start_without_ttl(self):
        from src.raguard.store import InMemoryTokenStore

        store = InMemoryTokenStore(
            token_ttl_seconds=None,
            sweep_interval_seconds=1,
        )
        assert store._sweep_thread is None

    def test_stop_sweep_is_safe_when_no_sweep(self):
        from src.raguard.store import InMemoryTokenStore

        store = InMemoryTokenStore()
        store.stop_sweep()  # Should not raise


class TestMaxSessions:
    """max_sessions caps the number of tracked sessions."""

    def test_oldest_session_evicted(self):
        from src.raguard.store import InMemoryTokenStore

        store = InMemoryTokenStore(max_sessions=2)
        store.add_token("s1", "tok_a")
        store.add_token("s2", "tok_b")
        store.add_token("s3", "tok_c")  # Should evict s1

        assert store.get_tokens("s1") == []
        assert store.get_tokens("s2") == ["tok_b"]
        assert store.get_tokens("s3") == ["tok_c"]

    def test_unlimited_sessions_by_default(self):
        from src.raguard.store import InMemoryTokenStore

        store = InMemoryTokenStore()
        for i in range(1000):
            store.add_token(f"s{i}", f"tok_{i}")
        assert len(store._tokens) == 1000


# --- Recursion Depth ---


class TestRecursionDepth:
    """FastAPI adapter injection respects max recursion depth."""

    def test_deeply_nested_json_no_crash(self):
        """50-level nested JSON does not crash."""
        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        app = MagicMock()
        adapter = RAGuardFastAPIMiddleware(app)

        # Build 50-level nested dict
        data: dict = {"text": "leaf"}
        for _ in range(50):
            data = {"nested": data}

        token = "TEST_TOKEN_123"
        adapter._inject_into_json(data, token)

        # Should not crash; leaf may or may not have token depending on depth
        # The point is no RecursionError


# --- Async Parity: decode_response ---


class TestAsyncDecodeResponse:
    """is_safe_async must check decode_response candidates like is_safe does."""

    async def test_async_base64_detected_with_decode(self):
        import base64

        mw = CanaryMiddleware(decode_response=True)
        token = mw.generate_token("s1")
        encoded = base64.b64encode(token.encode()).decode()
        assert not await mw.is_safe_async(encoded, "s1")

    async def test_async_base64_missed_without_decode(self):
        import base64

        mw = CanaryMiddleware(decode_response=False)
        token = mw.generate_token("s1")
        encoded = base64.b64encode(token.encode()).decode()
        assert await mw.is_safe_async(encoded, "s1")

    async def test_async_rot13_detected_with_decode(self):
        import codecs

        mw = CanaryMiddleware(decode_response=True)
        token = mw.generate_token("s1")
        encoded = codecs.encode(token, "rot_13")
        assert not await mw.is_safe_async(encoded, "s1")

    async def test_async_reversed_detected_with_decode(self):
        mw = CanaryMiddleware(decode_response=True)
        token = mw.generate_token("s1")
        reversed_token = token[::-1]
        assert not await mw.is_safe_async(reversed_token, "s1")

    async def test_async_character_splitting_detected_with_decode(self):
        mw = CanaryMiddleware(decode_response=True)
        token = mw.generate_token("s1")
        split_token = " ".join(token)
        assert not await mw.is_safe_async(split_token, "s1")


# --- Async Parity: fail_open ---


class TestAsyncGracefulDegradation:
    """is_safe_async must handle store errors with fail_open like is_safe does."""

    def _make_failing_store(self):
        class FailingStore:
            def add_token(self, session_id, token):
                raise RuntimeError("store down")

            def get_tokens(self, session_id):
                raise RuntimeError("store down")

            def has_token_in(self, session_id, text):
                raise RuntimeError("store down")

            def clear_session(self, session_id):
                raise RuntimeError("store down")

        return FailingStore()

    async def test_async_is_safe_fail_open_returns_true(self):
        """With fail_open=True, is_safe_async returns True on store error."""
        mw = CanaryMiddleware(
            config=RAGuardConfig(fail_open=True),
            store=self._make_failing_store(),
        )
        assert await mw.is_safe_async("any response", "s1") is True

    async def test_async_fail_closed_propagates_exception(self):
        """With fail_open=False, is_safe_async store errors propagate."""
        mw = CanaryMiddleware(
            config=RAGuardConfig(fail_open=False),
            store=self._make_failing_store(),
        )
        with pytest.raises(RuntimeError, match="store down"):
            await mw.is_safe_async("response", "s1")


# --- Max Scan Body Bytes ---


class TestMaxScanBodyBytes:
    """max_scan_body_bytes config validation."""

    def test_default_is_1mb(self):
        config = RAGuardConfig()
        assert config.max_scan_body_bytes == 1_048_576

    def test_custom_value_accepted(self):
        config = RAGuardConfig(max_scan_body_bytes=2_000_000)
        assert config.max_scan_body_bytes == 2_000_000

    def test_minimum_enforced(self):
        with pytest.raises(ValidationError):
            RAGuardConfig(max_scan_body_bytes=512)  # type: ignore[arg-type]

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("RAGUARD_MAX_SCAN_BODY_BYTES", "5000")
        config = RAGuardConfig()
        assert config.max_scan_body_bytes == 5000


# --- JSON Logging ---


class TestJSONLogging:
    """Structured JSON logging opt-in."""

    def test_json_logging_default_off(self):
        config = RAGuardConfig()
        assert config.json_logging is False

    def test_json_logging_configurable(self):
        config = RAGuardConfig(json_logging=True)
        assert config.json_logging is True

    def test_json_formatter_output(self):
        """JSON formatter produces valid JSON with expected keys."""
        import logging

        from src.raguard.core import _JSONFormatter

        formatter = _JSONFormatter()
        record = logging.LogRecord(
            name="raguard.core",
            level=logging.WARNING,
            pathname="core.py",
            lineno=1,
            msg="Exfiltration detected for session '%s'",
            args=("user_123",),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "WARNING"
        assert parsed["logger"] == "raguard.core"
        assert "user_123" in parsed["message"]
        assert "timestamp" in parsed

    def test_json_logging_configures_handler(self):
        """When json_logging=True, the raguard logger gets a JSON handler."""
        import logging

        import src.raguard.core as core_module
        from src.raguard.core import _JSONFormatter

        # Reset the idempotency guard so we can test
        original = core_module._JSON_LOGGING_CONFIGURED
        core_module._JSON_LOGGING_CONFIGURED = False
        try:
            CanaryMiddleware(json_logging=True)
            raguard_logger = logging.getLogger("raguard")
            assert any(
                isinstance(h.formatter, _JSONFormatter) for h in raguard_logger.handlers
            )
        finally:
            core_module._JSON_LOGGING_CONFIGURED = original
