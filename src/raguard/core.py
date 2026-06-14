"""Core engine for RAGuard: token generation, injection, and scanning."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import string
import urllib.request
from datetime import datetime, timezone
from typing import Any, overload

from .config import RAGuardConfig
from .metrics import RAGuardMetrics, _MetricsCollector
from .store import InMemoryTokenStore, TokenStore

logger = logging.getLogger(__name__)


class CanaryMiddleware:
    """Main entry point for RAGuard functionality."""

    def __init__(
        self,
        config: RAGuardConfig | None = None,
        store: TokenStore | None = None,
        **kwargs: Any,
    ):
        self.config = config or RAGuardConfig(**kwargs)
        self._store: TokenStore = store or InMemoryTokenStore(
            max_tokens_per_session=self.config.max_tokens_per_session,
            token_ttl_seconds=self.config.token_ttl_seconds,
        )
        # Backward-compat: expose _active_tokens for tests that
        # directly inspect internal state (e.g. FastAPI adapter tests).
        # Prefer using store methods for new code.
        self._active_tokens = _StoreProxy(self._store)
        # Circuit breaker state for webhook delivery
        self._cb_consecutive_failures: int = 0
        self._cb_last_failure_time: float = 0.0
        # Metrics
        self._metrics = _MetricsCollector()

    @property
    def metrics(self) -> RAGuardMetrics:
        """Return a snapshot of operational counters."""
        return self._metrics.snapshot()

    def generate_token(self, session_id: str) -> str:
        """Generate a unique token for a session.

        Tokens accumulate per session - multiple calls append to the session's
        token list. This supports multi-retrieval scenarios where inject() is
        called multiple times for the same session.
        """
        if self.config.stealth_mode:
            # Zero-width space (U+200B) and Zero-width non-joiner (U+200C)
            zw_chars = ["\u200b", "\u200c", "\u200d", "\ufeff"]
            token = "".join(
                secrets.choice(zw_chars) for _ in range(self.config.token_length)
            )
        else:
            alphabet = string.ascii_letters + string.digits
            token = "".join(
                secrets.choice(alphabet) for _ in range(self.config.token_length)
            )

        self._store.add_token(session_id, token)
        self._metrics.record_token_generated()
        return token

    def _format_injection(self, chunk: str, token: str) -> str:
        """Apply token_wrapper and injection_position to produce injected chunk."""
        wrapped = self.config.token_wrapper.format(token=token)
        if self.config.injection_position == "prepend":
            return f"{wrapped}{chunk}"
        return f"{chunk}{wrapped}"

    @overload
    def inject(self, chunks: str, session_id: str) -> str: ...

    @overload
    def inject(self, chunks: list[str], session_id: str) -> list[str]: ...

    def inject(self, chunks: str | list[str], session_id: str) -> str | list[str]:
        """Inject the canary token into the retrieved chunks."""
        try:
            token = self.generate_token(session_id)
        except Exception:
            if not self.config.fail_open:
                raise
            logger.warning(
                "RAGuard: Store error during inject — returning unmodified chunks",
                exc_info=True,
            )
            return chunks
        if isinstance(chunks, list):
            return [self._format_injection(chunk, token) for chunk in chunks]
        return self._format_injection(chunks, token)

    def is_safe(self, response: str, session_id: str) -> bool:
        """Check if the response contains any canary token for this session.

        Scans all accumulated tokens for the session. Returns False if ANY
        token is detected, indicating potential exfiltration.
        """
        try:
            tokens = self._store.get_tokens(session_id)
        except Exception:
            if not self.config.fail_open:
                raise
            logger.warning(
                "RAGuard: Store error during is_safe — failing open",
                exc_info=True,
            )
            return True
        if not tokens:
            return True  # No token generated for this session, assume safe

        # Check for presence of any token (handling both alphanumeric and zero-width)
        for token in tokens:
            if token in response:
                self._trigger_alert(session_id, response)
                self._metrics.record_scan_blocked()
                return False

        # Optional: check decoded variants for encoding bypass detection
        if self.config.decode_response:
            candidates = self._decode_candidates(response)
            for candidate in candidates:
                for token in tokens:
                    if token in candidate:
                        self._trigger_alert(session_id, response)
                        self._metrics.record_scan_blocked()
                        return False

        self._metrics.record_scan_safe()
        return True

    def _decode_candidates(self, text: str) -> list[str]:
        """Generate decoded variants of response text for bypass detection.

        Uses lightweight pre-filters to skip transforms that cannot
        possibly match the input characteristics.
        """
        import base64
        import codecs

        candidates: list[str] = []

        # Base64: skip if text is too short or has low Base64-alphabet density
        if len(text) >= 4:
            b64_chars = set(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
            )
            b64_count = sum(1 for c in text if c in b64_chars)
            if b64_count / len(text) > 0.75:
                try:
                    decoded = base64.b64decode(text, validate=True).decode(
                        "utf-8", errors="ignore"
                    )
                    if decoded:
                        candidates.append(decoded)
                except Exception:
                    pass

        # ROT13 (always cheap — single-pass substitution)
        try:
            candidates.append(codecs.decode(text, "rot_13"))
        except Exception:
            pass

        # Hex: skip if stripped text contains non-hex characters
        stripped = text.replace(" ", "")
        if stripped and all(c in "0123456789abcdefABCDEF" for c in stripped):
            try:
                candidates.append(
                    bytes.fromhex(stripped).decode("utf-8", errors="ignore")
                )
            except Exception:
                pass

        # Reversed (always cheap — single slice)
        candidates.append(text[::-1])

        # Character-split collapse (remove spaces between chars)
        collapsed = text.replace(" ", "")
        if collapsed != text:
            candidates.append(collapsed)

        return candidates

    def _is_safe_webhook_target(self, url: str) -> bool:
        """Block SSRF-risky webhook URLs (private IPs, non-HTTP schemes)."""
        import ipaddress
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            logger.warning("RAGuard: Webhook URL blocked (non-HTTP scheme): %s", url)
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        try:
            addr = ipaddress.ip_address(hostname)
            if addr.is_private or addr.is_loopback or addr.is_link_local:
                logger.warning(
                    "RAGuard: Webhook URL blocked (private/loopback IP): %s", url
                )
                return False
        except ValueError:
            # hostname is a DNS name, not an IP — allow it
            pass

        return True

    def _is_circuit_open(self) -> bool:
        """Check if the webhook circuit breaker is open (too many failures)."""
        if self._cb_consecutive_failures >= (
            self.config.webhook_circuit_breaker_threshold
        ):
            import time

            elapsed = time.monotonic() - self._cb_last_failure_time
            if elapsed < self.config.webhook_circuit_breaker_reset_seconds:
                return True
            # Reset period elapsed — close the circuit (half-open)
            self._cb_consecutive_failures = 0
        return False

    def _record_webhook_success(self) -> None:
        if self._cb_consecutive_failures > 0:
            logger.info("RAGuard: Webhook circuit breaker closed — delivery resumed")
        self._cb_consecutive_failures = 0

    def _record_webhook_failure(self) -> None:
        import time

        self._cb_consecutive_failures += 1
        self._cb_last_failure_time = time.monotonic()
        if self._cb_consecutive_failures == (
            self.config.webhook_circuit_breaker_threshold
        ):
            logger.warning(
                "RAGuard: Webhook circuit breaker open — skipping delivery "
                "for %ds after %d consecutive failures",
                self.config.webhook_circuit_breaker_reset_seconds,
                self._cb_consecutive_failures,
            )

    def _build_alert_request(
        self, session_id: str, response: str
    ) -> urllib.request.Request | None:
        """Build the webhook request, or None if no webhook is configured."""
        webhook_url = self.config.alert_webhook_url
        if not webhook_url:
            return None

        if not self._is_safe_webhook_target(webhook_url):
            return None

        if self._is_circuit_open():
            return None

        snippet = (
            response[:500] if self.config.include_response_snippet else "[redacted]"
        )

        payload = json.dumps(
            {
                "event": "canary_token_detected",
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "response_snippet": snippet,
            }
        ).encode("utf-8")

        return urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    def _trigger_alert(self, session_id: str, response: str) -> None:
        """Log the alert and optionally fire a webhook (fire-and-forget)."""
        logger.warning("RAGuard: Exfiltration detected for session '%s'", session_id)

        req = self._build_alert_request(session_id, response)
        if req is None:
            return

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                logger.debug("Webhook delivered: status %s", resp.status)
            self._record_webhook_success()
            self._metrics.record_webhook_success()
        except (OSError, ValueError) as exc:
            logger.error("Webhook delivery failed: %s", exc)
            self._record_webhook_failure()
            self._metrics.record_webhook_failure()

    async def _trigger_alert_async(self, session_id: str, response: str) -> None:
        """Async webhook delivery using asyncio.to_thread."""
        logger.warning("RAGuard: Exfiltration detected for session '%s'", session_id)

        req = self._build_alert_request(session_id, response)
        if req is None:
            return

        try:
            await asyncio.to_thread(urllib.request.urlopen, req, timeout=5)
            self._record_webhook_success()
            self._metrics.record_webhook_success()
        except (OSError, ValueError) as exc:
            logger.error("Webhook delivery failed: %s", exc)
            self._record_webhook_failure()
            self._metrics.record_webhook_failure()

    async def is_safe_async(self, response: str, session_id: str) -> bool:
        """Async version of is_safe with non-blocking webhook delivery.

        The string scan itself is synchronous (fast, <1ms). The async benefit
        comes from non-blocking webhook I/O.
        """
        try:
            tokens = self._store.get_tokens(session_id)
        except Exception:
            if not self.config.fail_open:
                raise
            logger.warning(
                "RAGuard: Store error during is_safe_async — failing open",
                exc_info=True,
            )
            return True
        if not tokens:
            return True

        for token in tokens:
            if token in response:
                await self._trigger_alert_async(session_id, response)
                self._metrics.record_scan_blocked()
                return False

        # Check decoded variants for encoding bypass detection
        if self.config.decode_response:
            candidates = self._decode_candidates(response)
            for candidate in candidates:
                for token in tokens:
                    if token in candidate:
                        await self._trigger_alert_async(session_id, response)
                        self._metrics.record_scan_blocked()
                        return False

        self._metrics.record_scan_safe()
        return True

    @overload
    async def inject_async(self, chunks: str, session_id: str) -> str: ...

    @overload
    async def inject_async(self, chunks: list[str], session_id: str) -> list[str]: ...

    async def inject_async(
        self, chunks: str | list[str], session_id: str
    ) -> str | list[str]:
        """Async version of inject. Delegates to the synchronous implementation.

        Token generation and string interpolation are fast enough that no
        thread offloading is needed. This method exists for API symmetry
        with is_safe_async and to support future async token stores.
        """
        return self.inject(chunks, session_id)

    def clear_session(self, session_id: str) -> None:
        """Remove all active tokens for a session. Call after response is delivered.

        Prevents unbounded growth of token store in long-running processes.
        """
        self._store.clear_session(session_id)


class _StoreProxy:
    """Dict-like proxy over TokenStore for backward compatibility.

    Allows existing code using ``middleware._active_tokens.get(session_id)``
    or ``middleware._active_tokens[session_id]`` to keep working.
    """

    def __init__(self, store: TokenStore) -> None:
        self._store = store

    def get(self, session_id: str, default: list[str] | None = None) -> list[str]:
        tokens = self._store.get_tokens(session_id)
        if not tokens and default is not None:
            return default
        return tokens

    def __getitem__(self, session_id: str) -> list[str]:
        return self._store.get_tokens(session_id)

    def __contains__(self, session_id: str) -> bool:
        return bool(self._store.get_tokens(session_id))
