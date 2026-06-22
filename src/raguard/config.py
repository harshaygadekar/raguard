"""Configuration models for RAGuard."""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGuardConfig(BaseSettings):
    """Configuration for the RAGuard middleware.

    All fields can be set via environment variables with the ``RAGUARD_``
    prefix (e.g. ``RAGUARD_STEALTH_MODE=true``).
    """

    model_config = SettingsConfigDict(
        env_prefix="RAGUARD_",
        case_sensitive=False,
    )

    stealth_mode: bool = Field(
        default=False,
        description=(
            "If True, uses zero-width Unicode sequences. "
            "If False, uses alphanumeric strings."
        ),
    )

    token_length: int = Field(
        default=12, ge=8, le=32, description="Length of the generated token."
    )

    alert_webhook_url: str | None = Field(
        default=None, description="Optional webhook URL to trigger on detection."
    )

    max_tokens_per_session: int = Field(
        default=100,
        ge=1,
        description="Maximum tokens kept per session. Oldest evicted when exceeded.",
    )

    token_ttl_seconds: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Seconds before tokens expire. None means tokens never expire "
            "and must be cleaned up via clear_session()."
        ),
    )

    include_response_snippet: bool = Field(
        default=False,
        description=(
            "If True, webhook payload includes first 500 chars of the LLM "
            "response. If False, snippet is redacted."
        ),
    )

    webhook_circuit_breaker_threshold: int = Field(
        default=5,
        ge=1,
        description=(
            "Number of consecutive webhook failures before the circuit opens."
        ),
    )

    webhook_circuit_breaker_reset_seconds: int = Field(
        default=60,
        ge=1,
        description="Seconds to wait before retrying after circuit opens.",
    )

    fail_open: bool = Field(
        default=True,
        description=(
            "If True, store exceptions are caught and logged; inject() returns "
            "unmodified data and is_safe() returns True. If False, exceptions "
            "propagate to the caller."
        ),
    )

    decode_response: bool = Field(
        default=False,
        description=(
            "If True, is_safe() attempts common decode transforms "
            "(Base64, ROT13, hex, reversed, character-split collapse) "
            "before scanning. Increases latency but catches encoding bypasses."
        ),
    )

    injection_position: str = Field(
        default="append",
        description=(
            "Where to place the canary token in the chunk: "
            "'append' (end) or 'prepend' (start)."
        ),
    )

    token_wrapper: str = Field(
        default="\n\n[{token}]",
        description=(
            "Format string for wrapping the token. Must contain '{token}' placeholder."
        ),
    )

    max_scan_body_bytes: int | None = Field(
        default=1_048_576,
        ge=1,
        description=(
            "FastAPI scan-path response body size cap in bytes. Responses "
            "exceeding this are rejected without scanning (non-streaming: 413; "
            "streaming: SSE error frame) — fail-open for detection, protects the "
            "process from OOM. Set to None to disable. Env var: "
            "RAGUARD_MAX_SCAN_BODY_BYTES."
        ),
    )

    json_logging: bool = Field(
        default=False,
        description=(
            "If True, configures the 'raguard' logger to emit structured JSON "
            "lines. Useful for production log aggregators (Datadog, ELK, "
            "CloudWatch). If False, uses standard Python log formatting."
        ),
    )

    @field_validator("injection_position")
    @classmethod
    def validate_injection_position(cls, v: str) -> str:
        if v not in ("append", "prepend"):
            msg = f"injection_position must be 'append' or 'prepend', got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("alert_webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            msg = (
                f"Webhook URL must use http:// or https:// scheme, "
                f"got '{parsed.scheme}://'."
            )
            raise ValueError(msg)
        if not parsed.hostname:
            msg = "Webhook URL must include a hostname."
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_stealth_token_length(self) -> RAGuardConfig:
        """Enforce minimum token_length=16 for stealth mode (entropy floor)."""
        if self.stealth_mode and self.token_length < 16:
            msg = (
                f"stealth_mode requires token_length >= 16 for sufficient "
                f"entropy, got {self.token_length}."
            )
            raise ValueError(msg)
        return self
