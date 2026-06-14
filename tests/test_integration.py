"""Integration tests for RAGuard - full pipeline scenarios."""

from unittest.mock import MagicMock, patch

import pytest

from src.raguard.config import RAGuardConfig
from src.raguard.core import CanaryMiddleware
from src.raguard.exceptions import CanaryTokenDetected


def _check_import(module_name):
    """Check if a module can be imported."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def test_full_pipeline_safe():
    """inject → simulate LLM (clean) → is_safe returns True."""
    middleware = CanaryMiddleware(stealth_mode=False)
    session_id = "integration_test_1"

    # Step 1: Retrieve and inject
    retrieved_docs = [
        "Confidential: Q3 revenue is $5M",
        "Internal: API key is sk-123",
    ]
    _secure_docs = middleware.inject(retrieved_docs, session_id)

    # Step 2: Simulate safe LLM response (summarizes, doesn't leak)
    llm_response = "The Q3 revenue target is five million dollars."

    # Step 3: Validate
    assert middleware.is_safe(llm_response, session_id) is True


def test_full_pipeline_exfiltration():
    """inject → simulate LLM (leaks token) → is_safe returns False."""
    middleware = CanaryMiddleware(stealth_mode=False)
    session_id = "integration_test_2"

    # Step 1: Retrieve and inject
    retrieved_docs = ["Confidential: Q3 revenue is $5M"]
    secure_docs = middleware.inject(retrieved_docs, session_id)

    # Step 2: Simulate leaked response (attacker forces LLM to output context)
    llm_response = secure_docs[0]  # LLM outputs the injected context verbatim

    # Step 3: Validate - should detect exfiltration
    assert middleware.is_safe(llm_response, session_id) is False


def test_pipeline_with_webhook():
    """Full pipeline + webhook fires on detection."""
    config = RAGuardConfig(
        stealth_mode=False, alert_webhook_url="http://example.com/webhook"
    )
    middleware = CanaryMiddleware(config=config)
    session_id = "webhook_test"

    retrieved_docs = ["Secret document"]
    secure_docs = middleware.inject(retrieved_docs, session_id)

    leaked_response = secure_docs[0]

    with patch("src.raguard.core.urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = middleware.is_safe(leaked_response, session_id)

        assert result is False
        assert mock_urlopen.called


def test_pipeline_stealth_mode():
    """Full pipeline with stealth tokens."""
    middleware = CanaryMiddleware(stealth_mode=True, token_length=16)
    session_id = "stealth_test"

    retrieved_docs = ["Confidential data"]
    secure_docs = middleware.inject(retrieved_docs, session_id)

    # Verify zero-width characters were injected
    assert any(
        char in ["\u200b", "\u200c", "\u200d", "\ufeff"] for char in secure_docs[0]
    )

    # Safe response passes
    assert middleware.is_safe("Safe summary", session_id) is True

    # Leaked response blocked
    assert middleware.is_safe(secure_docs[0], session_id) is False


def test_multiple_sessions():
    """Two sessions don't cross-contaminate tokens."""
    middleware = CanaryMiddleware(stealth_mode=False)

    session_a = "session_a"
    session_b = "session_b"

    # Inject for session A
    docs_a = middleware.inject(["Secret A"], session_a)

    # Inject for session B
    docs_b = middleware.inject(["Secret B"], session_b)

    # Extract tokens
    token_a = docs_a[0].split("[")[1].split("]")[0]
    token_b = docs_b[0].split("[")[1].split("]")[0]

    # Session A's leaked response is blocked
    assert middleware.is_safe(f"Leaked: {token_a}", session_a) is False

    # But session B doesn't see session A's token as a leak
    assert middleware.is_safe(f"Leaked: {token_a}", session_b) is True

    # Session B's leaked response is blocked
    assert middleware.is_safe(f"Leaked: {token_b}", session_b) is False


def test_session_cleanup():
    """clear_session removes token, subsequent is_safe returns True."""
    middleware = CanaryMiddleware(stealth_mode=False)
    session_id = "cleanup_test"

    # Inject
    secure_docs = middleware.inject(["Secret"], session_id)
    token = secure_docs[0].split("[")[1].split("]")[0]

    # Leaked response is blocked
    assert middleware.is_safe(f"Leaked: {token}", session_id) is False

    # Clear session
    middleware.clear_session(session_id)

    # Now the same leaked response passes (no active tokens)
    assert middleware.is_safe(f"Leaked: {token}", session_id) is True


@pytest.mark.asyncio
async def test_async_full_pipeline():
    """Async pipeline: inject_async → is_safe_async."""
    middleware = CanaryMiddleware(stealth_mode=False)
    session_id = "async_integration"

    # Async inject
    secure_docs = await middleware.inject_async(["Secret"], session_id)

    # Async safe check
    safe_result = await middleware.is_safe_async("Safe summary", session_id)
    assert safe_result is True

    # Async leak detection
    leak_result = await middleware.is_safe_async(secure_docs[0], session_id)
    assert leak_result is False


def test_token_accumulation():
    """Multiple inject() calls accumulate tokens for same session."""
    middleware = CanaryMiddleware(stealth_mode=False)
    session_id = "accumulation_test"

    # First injection
    docs_1 = middleware.inject(["Doc 1"], session_id)
    token_1 = docs_1[0].split("[")[1].split("]")[0]

    # Second injection (same session)
    docs_2 = middleware.inject(["Doc 2"], session_id)
    token_2 = docs_2[0].split("[")[1].split("]")[0]

    # Both tokens are tracked
    assert middleware.is_safe(f"Leaked: {token_1}", session_id) is False
    assert middleware.is_safe(f"Leaked: {token_2}", session_id) is False

    # Safe response still passes
    assert middleware.is_safe("Safe summary", session_id) is True


@pytest.mark.skipif(not _check_import("langchain"), reason="langchain not installed")
def test_adapter_langchain_full_pipeline():
    """LangChain adapter: retriever → callback → LLM → scan."""
    from uuid import uuid4

    from src.raguard.adapters.langchain import RAGuardLangChainCallback

    callback = RAGuardLangChainCallback(session_id="langchain_test")

    # Simulate retriever
    mock_doc = MagicMock()
    mock_doc.page_content = "Confidential Q3 data"
    docs = [mock_doc]

    # Callback injects on retriever_end
    callback.on_retriever_end(docs, run_id=uuid4())

    # Extract injected token
    injected = docs[0].page_content
    token = injected.split("[")[1].split("]")[0]

    # Simulate safe LLM response
    safe_result = MagicMock()
    safe_result.generations = [[MagicMock(text="Q3 summary")]]
    callback.on_llm_end(safe_result, run_id=uuid4())  # Should not raise

    # Simulate leaked LLM response
    leaked_result = MagicMock()
    leaked_result.generations = [[MagicMock(text=f"Leaked: {token}")]]

    with pytest.raises(CanaryTokenDetected) as exc_info:
        callback.on_llm_end(leaked_result, run_id=uuid4())

    assert exc_info.value.session_id == "langchain_test"


@pytest.mark.skipif(
    not _check_import("llama_index"), reason="llama-index not installed"
)
def test_adapter_llamaindex_full_pipeline():
    """LlamaIndex adapter: postprocessor → scan_response."""
    from src.raguard.adapters.llamaindex import RAGuardLlamaIndexPostprocessor

    postprocessor = RAGuardLlamaIndexPostprocessor(session_id="llama_test")

    # Simulate nodes
    mock_node = MagicMock()
    mock_node.node = MagicMock()
    mock_node.node.get_content.return_value = "Confidential data"
    nodes = [mock_node]

    # Postprocess injects tokens
    _result_nodes = postprocessor.postprocess_nodes(nodes)

    # Get injected text
    injected_call = nodes[0].node.set_content.call_args
    injected_text = injected_call[0][0]
    token = injected_text.split("[")[1].split("]")[0]

    # Safe response
    assert postprocessor.scan_response("Safe summary") is True

    # Leaked response
    assert postprocessor.scan_response(f"Leaked: {token}") is False
