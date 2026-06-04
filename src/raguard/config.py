"""Configuration models for RAGuard."""

from pydantic import BaseModel, Field
from typing import Literal


class RAGuardConfig(BaseModel):
    """Configuration for the RAGuard middleware."""
    
    stealth_mode: bool = Field(
        default=False,
        description="If True, uses zero-width Unicode sequences. If False, uses alphanumeric strings."
    )
    
    token_length: int = Field(
        default=12,
        ge=8,
        le=32,
        description="Length of the generated token."
    )
    
    alert_webhook_url: str | None = Field(
        default=None,
        description="Optional webhook URL to trigger on detection."
    )