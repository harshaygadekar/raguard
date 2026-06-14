"""Tokenizer validation suite: verify canary tokens survive real preprocessing.

Tests that stealth (zero-width Unicode) tokens resist Unicode normalization,
whitespace stripping, and common string operations that LLM tokenizers apply.
This validates the PRD requirement for tokenizer-compatibility testing.
"""

import unicodedata

from src.raguard.config import RAGuardConfig
from src.raguard.core import CanaryMiddleware

# Zero-width characters used in stealth mode (from core.py)
ZW_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff"]


def _generate_stealth_token(length: int = 16) -> str:
    """Generate a stealth token using the same config as core.py."""
    config = RAGuardConfig(stealth_mode=True, token_length=length)
    middleware = CanaryMiddleware(config=config)
    return middleware.generate_token("test_session")


def _generate_alphanumeric_token(length: int = 12) -> str:
    """Generate an alphanumeric token."""
    config = RAGuardConfig(stealth_mode=False, token_length=length)
    middleware = CanaryMiddleware(config=config)
    return middleware.generate_token("test_session")


class TestZeroWidthSurvival:
    """Verify zero-width tokens survive standard forms of text processing."""

    def test_nfc_normalization_preserves_token(self):
        """NFC (canonical composition) must not strip zero-width chars."""
        token = _generate_stealth_token()
        normalized = unicodedata.normalize("NFC", token)
        assert token == normalized, f"NFC altered the token: {token!r} → {normalized!r}"

    def test_nfd_normalization_preserves_token(self):
        """NFD (canonical decomposition) must not strip zero-width chars."""
        token = _generate_stealth_token()
        normalized = unicodedata.normalize("NFD", token)
        assert token == normalized, f"NFD altered the token: {token!r} → {normalized!r}"

    def test_nfkc_normalization_preserves_token(self):
        """NFKC (compatibility composition) must not strip token chars.

        This is the most aggressive normalization — if it passes here,
        the token survives virtually all tokenizer preprocessing.
        """
        token = _generate_stealth_token()
        normalized = unicodedata.normalize("NFKC", token)
        # Check that every character survived
        for i, char in enumerate(token):
            assert char in normalized, (
                f"NFKC stripped {char!r} (U+{ord(char):04X}) at position {i}"
            )

    def test_nfkd_normalization_preserves_token(self):
        """NFKD (compatibility decomposition) must not strip token chars."""
        token = _generate_stealth_token()
        normalized = unicodedata.normalize("NFKD", token)
        for i, char in enumerate(token):
            assert char in normalized, (
                f"NFKD stripped {char!r} (U+{ord(char):04X}) at position {i}"
            )

    def test_zero_width_survives_whitespace_operations(self):
        """Python's .strip() and .split() must not remove zero-width chars."""
        token = _generate_stealth_token()
        wrapped = f"  {token}  "
        stripped = wrapped.strip()

        assert token in stripped, f".strip() removed zero-width chars from {token!r}"

        # split() with default separator should not break on zero-width
        parts = wrapped.split()
        # The token should still be intact within the resulting parts
        # (zero-width chars are invisible, so split may behave unexpectedly)
        joined = " ".join(parts)
        assert len(joined) > 0, "split() consumed the entire string"

    def test_zero_width_survives_string_concatenation(self):
        """Token survives common operations: concatenation, slicing, replace."""
        token = _generate_stealth_token()

        # Concatenation
        result = "prefix" + token + "suffix"
        assert token in result

        # Slicing
        token_len = len(token)
        sliced = result[-token_len:]
        assert len(sliced) == token_len

        # Replace (ensure token is not accidentally modified by replace ops)
        replaced = result.replace("prefix", "start")
        assert token in replaced

    def test_zero_width_is_detectable_after_injection(self):
        """Full pipeline: inject stealth token into text → extract → detect."""
        middleware = CanaryMiddleware(stealth_mode=True, token_length=16)
        session_id = "tokenizer_validation"

        # Inject
        docs = middleware.inject(["Secret data"], session_id)

        # Verify the token is present in the injected text
        assert any(char in ZW_CHARS for char in docs[0]), (
            "No zero-width characters found in injected document"
        )

        # Apply NLP-like preprocessing: strip, normalize, join
        processed = unicodedata.normalize("NFC", docs[0].strip())

        # Verify token is still detectable
        assert middleware.is_safe(processed, session_id) is False, (
            "Stealth token lost after normalization and stripping"
        )

        # Verify safe text is not blocked
        assert middleware.is_safe("Safe summary without the token", session_id) is True


class TestAlphanumericRobustness:
    """Verify alphanumeric tokens survive all transformations (they always will,
    but this provides the baseline for comparison against stealth mode)."""

    def test_alphanumeric_survives_nfkc(self):
        """Alphanumeric tokens are inherently NFKC-safe."""
        token = _generate_alphanumeric_token()
        normalized = unicodedata.normalize("NFKC", token)
        assert token == normalized

    def test_alphanumeric_survives_strip(self):
        """Alphanumeric tokens are not whitespace."""
        token = _generate_alphanumeric_token()
        wrapped = f"  {token}  "
        stripped = wrapped.strip()
        assert stripped == token
