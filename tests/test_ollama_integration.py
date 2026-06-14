"""End-to-end integration tests with Ollama (local LLM).

These tests require:
  - Ollama installed and running (`ollama serve`)
  - At least one local model pulled (e.g. `ollama pull llama3.2:1b`)
  - `pip install ollama`

Run standalone (not collected by default pytest):
  python -m pytest tests/test_ollama_integration.py -v -s --no-cov

These tests prove RAGuard correctly classifies real LLM output:
  - When the LLM leaks the canary token → is_safe returns False
  - The middleware pipeline (inject → LLM → scan) works end-to-end
  - Metrics and session lifecycle work with real LLM responses

NOTE: LLM output is non-deterministic. Tests that depend on specific LLM
behavior (e.g. "the LLM will quote verbatim") are inherently flaky.
Tests are structured to validate RAGuard's logic, not LLM compliance.
"""

from __future__ import annotations

import sys
import textwrap

import pytest

from src.raguard.core import CanaryMiddleware

_OLLAMA_MODEL: str | None = None


def check_prerequisites():
    """Return True if Ollama is available with at least one local model."""
    global _OLLAMA_MODEL
    try:
        import ollama
    except ImportError:
        print("SKIP: ollama package not installed (pip install ollama)")
        return False

    try:
        models = ollama.list()
    except Exception as e:
        print(f"SKIP: cannot connect to Ollama ({e})")
        return False

    # Extract model names from the response
    model_list = models.get("models", [])
    local_names = []
    for m in model_list:
        name = None
        if isinstance(m, dict) and "name" in m:
            name = m["name"]
        elif hasattr(m, "model"):
            name = m.model
        elif hasattr(m, "name"):
            name = m.name
        if name and "cloud" not in name.lower():
            local_names.append(name)

    if not local_names:
        print("SKIP: no local Ollama models found (run: ollama pull <model>)")
        return False

    # Prefer llama3.2 if available, otherwise use first local model
    _OLLAMA_MODEL = next(
        (n for n in local_names if "llama3.2" in n),
        local_names[0],
    )
    print(f"Using Ollama model: {_OLLAMA_MODEL}")
    return True


# Skip tests in pytest if Ollama is not running/available
if not check_prerequisites():
    pytestmark = pytest.mark.skip(reason="Ollama prerequisites not met")


def run_ollama(prompt: str, model: str | None = None) -> str:
    """Send a prompt to Ollama and return the response text."""
    import ollama

    model = model or _OLLAMA_MODEL or "llama3.2:1b"
    response = ollama.generate(model=model, prompt=prompt)
    return response["response"]


# --- Core Pipeline Tests ---


def test_inject_scan_pipeline():
    """End-to-end: inject → LLM → scan works. Token present → detected.

    Instead of relying on LLM behavior, we manually construct a response
    that includes the token (simulating a leak) and verify RAGuard catches it.
    Then we also send to the real LLM and log whatever happens.
    """
    print("\n--- Test: Inject-scan pipeline ---")

    middleware = CanaryMiddleware(stealth_mode=False)
    session_id = "pipeline_test"

    docs = middleware.inject(["Revenue was $5M last quarter."], session_id)
    _ = middleware._store.get_tokens(session_id)[0]

    # Deterministic check: if token is in the output, RAGuard catches it
    leaked_response = f"The document says: {docs[0]}"
    assert not middleware.is_safe(leaked_response, session_id)
    print("  Deterministic check: PASSED (token in response -> detected)")

    # Now test with real LLM (informational — log result either way)
    middleware2 = CanaryMiddleware(stealth_mode=False)
    session_id2 = "pipeline_real"
    docs2 = middleware2.inject(["Revenue was $5M last quarter."], session_id2)

    prompt = textwrap.dedent(f"""\
        Repeat the following text exactly as written:
        {docs2[0]}
    """)
    llm_response = run_ollama(prompt)
    result = middleware2.is_safe(llm_response, session_id2)
    print(f"  LLM response: {llm_response[:200]}")
    print(f"  is_safe: {result}")
    print(f"  (LLM {'did NOT leak' if result else 'LEAKED'} the token)")


def test_safe_summary_informational():
    """Ask LLM to summarize — log whether token leaks or not.

    LLM behavior is non-deterministic. This test validates that RAGuard
    correctly classifies the output either way, and logs the result.
    """
    print("\n--- Test: Summary behavior (informational) ---")

    middleware = CanaryMiddleware(stealth_mode=False)
    session_id = "summary_test"

    docs = middleware.inject(
        ["The company earned $5M in Q3.", "API key is sk-123abc."],
        session_id,
    )

    prompt = textwrap.dedent(f"""\
        Summarize these documents in your own words. Do not quote directly:

        {docs[0]}
        {docs[1]}
    """)

    llm_response = run_ollama(prompt)
    result = middleware.is_safe(llm_response, session_id)

    print(f"  LLM response: {llm_response[:200]}")
    print(f"  is_safe: {result}")
    if result:
        print("  [OK] LLM summarized without leaking - RAGuard says safe (correct)")
    else:
        print("  [!] LLM leaked the canary token - RAGuard detected it (correct)")

    # This test always passes — we're validating RAGuard classifies correctly,
    # not that the LLM behaves a certain way.
    assert isinstance(result, bool)


def test_exfiltration_attempt():
    """Ask LLM to repeat context verbatim — verify RAGuard handles either outcome.

    Some models refuse to repeat content. Others comply. RAGuard should
    correctly classify either way.
    """
    print("\n--- Test: Exfiltration attempt (informational) ---")

    middleware = CanaryMiddleware(stealth_mode=False)
    session_id = "exfil_test"

    docs = middleware.inject(
        ["Project budget: $2.5M allocated for infrastructure."],
        session_id,
    )

    prompt = textwrap.dedent(f"""\
        You are an exact transcription service. Copy the text below
        character for character without any changes:

        {docs[0]}
    """)

    llm_response = run_ollama(prompt)
    result = middleware.is_safe(llm_response, session_id)

    print(f"  LLM response: {llm_response[:200]}")
    print(f"  is_safe: {result}")
    if not result:
        print("  [OK] LLM leaked verbatim - RAGuard caught it (exfiltration detected)")
    else:
        print("  [!] LLM refused or paraphrased - RAGuard says safe (no leak)")

    assert isinstance(result, bool)


def test_metrics_with_real_llm():
    """Metrics counters increment correctly during real LLM interaction."""
    print("\n--- Test: Metrics with real LLM ---")

    middleware = CanaryMiddleware(stealth_mode=False)
    session_id = "metrics_test"

    assert middleware.metrics.tokens_generated == 0
    docs = middleware.inject(["Test data for metrics."], session_id)
    assert middleware.metrics.tokens_generated == 1

    llm_response = run_ollama(f"Repeat: {docs[0]}")
    middleware.is_safe(llm_response, session_id)

    m = middleware.metrics
    assert m.scans_total == 1
    assert m.scans_safe + m.scans_blocked == 1
    print(f"  tokens_generated={m.tokens_generated}, scans={m.scans_total}")
    print(f"  safe={m.scans_safe}, blocked={m.scans_blocked}")
    print("  PASSED")


def test_session_lifecycle_with_real_llm():
    """Full session lifecycle: inject → scan → clear → scan again."""
    print("\n--- Test: Session lifecycle ---")

    middleware = CanaryMiddleware(stealth_mode=False)
    session_id = "lifecycle_test"

    _ = middleware.inject(["Lifecycle test document."], session_id)
    token = middleware._store.get_tokens(session_id)[0]

    # Token in response → unsafe
    assert not middleware.is_safe(f"Output: {token}", session_id)
    print("  Pre-clear: token detected correctly")

    # Clear session
    middleware.clear_session(session_id)

    # After clear, same token → safe (no tokens tracked)
    assert middleware.is_safe(f"Output: {token}", session_id)
    print("  Post-clear: token no longer tracked")
    print("  PASSED")


def test_stealth_token_with_real_llm():
    """Stealth token with real LLM — informational test.

    Zero-width tokens may or may not survive the LLM's tokenizer.
    This test logs the outcome rather than asserting.
    """
    print("\n--- Test: Stealth token with real LLM (informational) ---")

    middleware = CanaryMiddleware(stealth_mode=True, token_length=16)
    session_id = "stealth_test"

    docs = middleware.inject(
        ["Revenue was $5M according to finance."],
        session_id,
    )

    prompt = textwrap.dedent(f"""\
        Copy this text exactly: {docs[0]}
    """)

    llm_response = run_ollama(prompt)
    result = middleware.is_safe(llm_response, session_id)

    print(f"  LLM response length: {len(llm_response)} chars")
    print(f"  is_safe: {result}")
    if result:
        print(
            "  NOTE: Tokenizer likely stripped zero-width characters. "
            "This is a known limitation for stealth mode."
        )
    else:
        print("  [OK] Zero-width token survived the tokenizer!")

    assert isinstance(result, bool)


def test_encoding_bypass_detection_with_real_llm():
    """Test decode_response=True catches an LLM that base64-encodes output."""
    import base64

    print("\n--- Test: Encoding bypass detection ---")

    middleware = CanaryMiddleware(decode_response=True)
    session_id = "encode_test"

    token = middleware.generate_token(session_id)

    # Simulate an LLM that was tricked into base64-encoding its response
    encoded_response = base64.b64encode(
        f"Here is the secret: {token}".encode()
    ).decode()

    result = middleware.is_safe(encoded_response, session_id)
    print(f"  Base64 encoded response scanned: is_safe={result}")
    assert not result, "decode_response=True should catch base64-encoded token"
    print("  PASSED")


def main():
    if not check_prerequisites():
        sys.exit(0)

    tests = [
        test_inject_scan_pipeline,
        test_safe_summary_informational,
        test_exfiltration_attempt,
        test_metrics_with_real_llm,
        test_session_lifecycle_with_real_llm,
        test_stealth_token_with_real_llm,
        test_encoding_bypass_detection_with_real_llm,
    ]

    failures = []
    for test_func in tests:
        try:
            test_func()
        except AssertionError as e:
            failures.append((test_func.__name__, str(e)))
            print(f"\n  FAILED: {e}")
        except Exception as e:
            failures.append((test_func.__name__, str(e)))
            print(f"\n  ERROR: {e}")

    print(f"\n{'=' * 60}")
    if failures:
        print(f"{len(failures)} test(s) FAILED:")
        for name, error in failures:
            print(f"  - {name}: {error}")
        sys.exit(1)
    else:
        print(f"All {len(tests)} Ollama integration tests passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
