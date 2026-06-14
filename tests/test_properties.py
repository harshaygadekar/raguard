"""Property-based tests for RAGuard using Hypothesis.

Verifies token generation invariants hold across thousands of random inputs.
"""

import string

from hypothesis import given, settings
from hypothesis import strategies as st

from src.raguard.config import RAGuardConfig
from src.raguard.core import CanaryMiddleware

ZW_CHARS = {"\u200b", "\u200c", "\u200d", "\ufeff"}
ALPHANUMERIC = set(string.ascii_letters + string.digits)


@given(length=st.integers(min_value=8, max_value=32))
@settings(max_examples=200)
def test_alphanumeric_token_invariants(length: int):
    """Alphanumeric tokens: correct length, all alphanumeric chars."""
    config = RAGuardConfig(stealth_mode=False, token_length=length)
    mw = CanaryMiddleware(config=config)
    token = mw.generate_token("prop_session")
    assert len(token) == length
    assert all(c in ALPHANUMERIC for c in token)


@given(length=st.integers(min_value=16, max_value=32))
@settings(max_examples=200)
def test_stealth_token_invariants(length: int):
    """Stealth tokens: correct length, all zero-width chars."""
    config = RAGuardConfig(stealth_mode=True, token_length=length)
    mw = CanaryMiddleware(config=config)
    token = mw.generate_token("prop_session")
    assert len(token) == length
    assert all(c in ZW_CHARS for c in token)


@given(
    text=st.text(min_size=0, max_size=500),
    length=st.integers(min_value=8, max_value=32),
)
@settings(max_examples=200)
def test_injected_token_always_detectable(text: str, length: int):
    """Any generated token is detectable when present in the response."""
    config = RAGuardConfig(stealth_mode=False, token_length=length)
    mw = CanaryMiddleware(config=config)
    injected = mw.inject(text, "prop_session")
    assert not mw.is_safe(injected, "prop_session")


@given(
    text=st.text(
        alphabet=st.characters(
            categories=("L", "N", "P", "Z"),
            exclude_characters=string.ascii_letters + string.digits,
        ),
        min_size=1,
        max_size=200,
    ),
)
@settings(max_examples=200)
def test_safe_text_returns_true(text: str):
    """Text that does NOT contain the generated token returns True."""
    mw = CanaryMiddleware()
    sid = "prop_session"
    mw.generate_token(sid)
    # The random text (no ascii letters/digits) can't contain our alphanumeric token
    assert mw.is_safe(text, sid)


@given(chunks=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=10))
@settings(max_examples=100)
def test_inject_output_always_contains_token(chunks: list[str]):
    """inject() output always contains the generated token."""
    mw = CanaryMiddleware()
    sid = "prop_session"
    result = mw.inject(chunks, sid)
    assert isinstance(result, list)
    assert len(result) == len(chunks)
    # Every chunk should contain the token
    tokens = mw._store.get_tokens(sid)
    assert len(tokens) == 1
    token = tokens[0]
    for chunk in result:
        assert token in chunk
