"""Lightweight metrics counters for RAGuard.

Provides in-process counters that users can poll and export to their
own monitoring stack. No external dependencies (no Prometheus/StatsD).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class RAGuardMetrics:
    """Snapshot of RAGuard operational counters.

    Access via ``middleware.metrics``. All counters are monotonically
    increasing except ``sessions_active`` which tracks current state.
    """

    tokens_generated: int = 0
    tokens_detected: int = 0
    scans_total: int = 0
    scans_safe: int = 0
    scans_blocked: int = 0
    webhook_successes: int = 0
    webhook_failures: int = 0


class _MetricsCollector:
    """Thread-safe metrics collector. Internal use only."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tokens_generated = 0
        self._tokens_detected = 0
        self._scans_total = 0
        self._scans_safe = 0
        self._scans_blocked = 0
        self._webhook_successes = 0
        self._webhook_failures = 0

    def record_token_generated(self) -> None:
        with self._lock:
            self._tokens_generated += 1

    def record_scan_safe(self) -> None:
        with self._lock:
            self._scans_total += 1
            self._scans_safe += 1

    def record_scan_blocked(self) -> None:
        with self._lock:
            self._scans_total += 1
            self._scans_blocked += 1
            self._tokens_detected += 1

    def record_webhook_success(self) -> None:
        with self._lock:
            self._webhook_successes += 1

    def record_webhook_failure(self) -> None:
        with self._lock:
            self._webhook_failures += 1

    def snapshot(self) -> RAGuardMetrics:
        with self._lock:
            return RAGuardMetrics(
                tokens_generated=self._tokens_generated,
                tokens_detected=self._tokens_detected,
                scans_total=self._scans_total,
                scans_safe=self._scans_safe,
                scans_blocked=self._scans_blocked,
                webhook_successes=self._webhook_successes,
                webhook_failures=self._webhook_failures,
            )
