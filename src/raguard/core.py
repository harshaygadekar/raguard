"""Core engine for RAGuard: token generation, injection, and scanning."""

import secrets
import string
import re
from typing import List, Union

from .config import RAGuardConfig


class CanaryMiddleware:
    """Main entry point for RAGuard functionality."""
    
    def __init__(self, config: RAGuardConfig | None = None, **kwargs):
        self.config = config or RAGuardConfig(**kwargs)
        self._active_tokens: dict[str, str] = {}

    def generate_token(self, session_id: str) -> str:
        """Generate a unique token for a session."""
        if self.config.stealth_mode:
            # Zero-width space (U+200B) and Zero-width non-joiner (U+200C)
            zw_chars = ['\u200b', '\u200c', '\u200d', '\ufeff']
            token = "".join(secrets.choice(zw_chars) for _ in range(self.config.token_length))
        else:
            alphabet = string.ascii_letters + string.digits
            token = "".join(secrets.choice(alphabet) for _ in range(self.config.token_length))
            
        self._active_tokens[session_id] = token
        return token

    def inject(self, chunks: Union[str, List[str]], session_id: str) -> Union[str, List[str]]:
        """Inject the canary token into the retrieved chunks."""
        token = self.generate_token(session_id)
        # Append token to the end of the context
        if isinstance(chunks, list):
            return [f"{chunk}\n\n[{token}]" for chunk in chunks]
        return f"{chunks}\n\n[{token}]"

    def is_safe(self, response: str, session_id: str) -> bool:
        """Check if the response contains the canary token."""
        token = self._active_tokens.get(session_id)
        if not token:
            return True  # No token generated for this session, assume safe
            
        # Check for token presence (handling both alphanumeric and zero-width)
        if token in response:
            self._trigger_alert(session_id, response)
            return False
            
        return True

    def _trigger_alert(self, session_id: str, response: str) -> None:
        """Handle alerting logic when a token is detected."""
        # TODO: Implement webhook logic if config.alert_webhook_url is set
        print(f"[RAGUARD ALERT] Exfiltration attempt detected for session: {session_id}")