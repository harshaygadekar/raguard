"""Unit tests for RAGuard framework adapters."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.raguard.core import CanaryMiddleware
from src.raguard.exceptions import CanaryTokenDetected

# Skip decorators for optional dependencies
try:
    import langchain  # noqa: F401

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    import llama_index  # noqa: F401

    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False

skip_if_no_langchain = pytest.mark.skipif(
    not LANGCHAIN_AVAILABLE, reason="langchain not installed"
)
skip_if_no_llamaindex = pytest.mark.skipif(
    not LLAMAINDEX_AVAILABLE, reason="llama-index not installed"
)


# ============================================================================
# Test Helpers
# ============================================================================


def _make_mock_document(content: str) -> MagicMock:
    """Create a mock LangChain Document."""
    doc = MagicMock()
    doc.page_content = content
    return doc


def _make_mock_llm_result(texts: list[str]) -> MagicMock:
    """Create a mock LangChain LLMResult."""
    result = MagicMock()
    generations = []
    for text in texts:
        gen = MagicMock()
        gen.text = text
        generations.append([gen])
    result.generations = generations
    return result


def _make_mock_node_with_score(content: str) -> MagicMock:
    """Create a mock LlamaIndex NodeWithScore."""
    node_ws = MagicMock()
    node_ws.node = MagicMock()
    node_ws.node.get_content.return_value = content
    return node_ws


# ============================================================================
# TestLangChainAdapter
# ============================================================================


@skip_if_no_langchain
class TestLangChainAdapter:
    """Tests for RAGuardLangChainCallback."""

    def test_inject_on_retriever_end(self):
        """page_content is modified after callback."""
        from src.raguard.adapters.langchain import RAGuardLangChainCallback

        callback = RAGuardLangChainCallback(session_id="test_session")
        docs = [
            _make_mock_document("Document A content"),
            _make_mock_document("Document B content"),
        ]

        callback.on_retriever_end(
            documents=docs,
            run_id=uuid4(),
        )

        # Verify tokens were injected
        assert "[" in docs[0].page_content and "]" in docs[0].page_content
        assert "[" in docs[1].page_content and "]" in docs[1].page_content

    def test_scan_safe_on_llm_end(self):
        """No exception when response is clean."""
        from src.raguard.adapters.langchain import RAGuardLangChainCallback

        callback = RAGuardLangChainCallback(session_id="test_session")

        # Inject tokens first
        docs = [_make_mock_document("Secret content")]
        callback.on_retriever_end(docs, run_id=uuid4())

        # Scan safe response
        safe_result = _make_mock_llm_result(["This is a safe summary"])

        # Should not raise
        callback.on_llm_end(safe_result, run_id=uuid4())

    def test_scan_detects_on_llm_end(self):
        """CanaryTokenDetected raised when token is in generation."""
        from src.raguard.adapters.langchain import RAGuardLangChainCallback

        callback = RAGuardLangChainCallback(session_id="test_session")

        # Inject tokens
        docs = [_make_mock_document("Secret content")]
        callback.on_retriever_end(docs, run_id=uuid4())

        # Get the injected token from the document
        injected_content = docs[0].page_content
        token_start = injected_content.rfind("[") + 1
        token_end = injected_content.rfind("]")
        token = injected_content[token_start:token_end]

        # Scan leaked response
        leaked_result = _make_mock_llm_result([f"Here is the secret: {token}"])

        with pytest.raises(CanaryTokenDetected) as exc_info:
            callback.on_llm_end(leaked_result, run_id=uuid4())

        assert exc_info.value.session_id == "test_session"

    def test_multiple_generations_scanned(self):
        """All generations in LLMResult.generations are checked."""
        from src.raguard.adapters.langchain import RAGuardLangChainCallback

        callback = RAGuardLangChainCallback(session_id="test_session")

        # Inject tokens
        docs = [_make_mock_document("Secret")]
        callback.on_retriever_end(docs, run_id=uuid4())

        # Extract token
        injected_content = docs[0].page_content
        token_start = injected_content.rfind("[") + 1
        token_end = injected_content.rfind("]")
        token = injected_content[token_start:token_end]

        # Multiple generations, second one leaks
        leaked_result = _make_mock_llm_result(
            [
                "Safe generation 1",
                f"Leaked generation 2: {token}",
            ]
        )

        with pytest.raises(CanaryTokenDetected):
            callback.on_llm_end(leaked_result, run_id=uuid4())

    def test_middleware_shared_instance(self):
        """Pre-built middleware can be passed in."""
        from src.raguard.adapters.langchain import RAGuardLangChainCallback

        middleware = CanaryMiddleware(stealth_mode=True, token_length=16)
        callback = RAGuardLangChainCallback(
            session_id="test_session", middleware=middleware
        )

        assert callback.middleware is middleware

    def test_default_config(self):
        """Default config is created when none provided."""
        from src.raguard.adapters.langchain import RAGuardLangChainCallback

        callback = RAGuardLangChainCallback(session_id="test_session")

        assert callback.middleware is not None
        assert callback.session_id == "test_session"


# ============================================================================
# TestLlamaIndexAdapter
# ============================================================================


@skip_if_no_llamaindex
class TestLlamaIndexAdapter:
    """Tests for RAGuardLlamaIndexPostprocessor."""

    def test_inject_into_nodes(self):
        """Node text is modified after postprocessing."""
        from src.raguard.adapters.llamaindex import RAGuardLlamaIndexPostprocessor

        postprocessor = RAGuardLlamaIndexPostprocessor(session_id="test_session")
        nodes = [
            _make_mock_node_with_score("Node A content"),
            _make_mock_node_with_score("Node B content"),
        ]

        postprocessor.postprocess_nodes(nodes)

        # Verify set_content was called on each node
        assert nodes[0].node.set_content.called
        assert nodes[1].node.set_content.called

    def test_postprocess_returns_nodes(self):
        """Returns the same list (not a copy)."""
        from src.raguard.adapters.llamaindex import RAGuardLlamaIndexPostprocessor

        postprocessor = RAGuardLlamaIndexPostprocessor(session_id="test_session")
        nodes = [_make_mock_node_with_score("Content")]

        result = postprocessor.postprocess_nodes(nodes)

        assert result is nodes

    def test_scan_response_safe(self):
        """scan_response returns True for clean text."""
        from src.raguard.adapters.llamaindex import RAGuardLlamaIndexPostprocessor

        postprocessor = RAGuardLlamaIndexPostprocessor(session_id="test_session")

        # Inject tokens first
        nodes = [_make_mock_node_with_score("Secret")]
        postprocessor.postprocess_nodes(nodes)

        # Scan safe response
        result = postprocessor.scan_response("This is a safe summary")

        assert result is True

    def test_scan_response_detected(self):
        """scan_response returns False for leaked token."""
        from src.raguard.adapters.llamaindex import RAGuardLlamaIndexPostprocessor

        postprocessor = RAGuardLlamaIndexPostprocessor(session_id="test_session")

        # Inject tokens
        nodes = [_make_mock_node_with_score("Secret")]
        postprocessor.postprocess_nodes(nodes)

        # Get the token that was injected
        injected_call = nodes[0].node.set_content.call_args
        injected_text = injected_call[0][0]
        token_start = injected_text.rfind("[") + 1
        token_end = injected_text.rfind("]")
        token = injected_text[token_start:token_end]

        # Scan leaked response
        result = postprocessor.scan_response(f"Leaked: {token}")

        assert result is False

    def test_empty_nodes(self):
        """Handles empty list gracefully."""
        from src.raguard.adapters.llamaindex import RAGuardLlamaIndexPostprocessor

        postprocessor = RAGuardLlamaIndexPostprocessor(session_id="test_session")

        result = postprocessor.postprocess_nodes([])

        assert result == []


# ============================================================================
# TestFastAPIAdapter
# ============================================================================


class TestFastAPIAdapter:
    """Tests for RAGuardFastAPIMiddleware."""

    def test_passthrough_unconfigured_paths(self):
        """Requests to non-configured paths pass through."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        async def other_endpoint(request):
            return JSONResponse({"data": "test"})

        app = Starlette(routes=[Route("/api/other", other_endpoint)])
        app.add_middleware(RAGuardFastAPIMiddleware)

        client = TestClient(app)
        response = client.get("/api/other")

        assert response.status_code == 200
        assert response.json() == {"data": "test"}

    def test_session_id_from_header(self):
        """Session ID extracted from X-Session-ID header."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        async def retrieve(request):
            return JSONResponse({"doc": "Secret"})

        app = Starlette(routes=[Route("/api/retrieve", retrieve)])
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            inject_paths=[r"/api/retrieve"],
        )

        client = TestClient(app)
        response = client.get(
            "/api/retrieve", headers={"X-Session-ID": "custom_session"}
        )

        # Verify canary token was added to response headers
        assert "x-canary-token" in response.headers

    def test_session_id_default(self):
        """Falls back to 'default' when header missing."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        async def retrieve(request):
            return JSONResponse({"doc": "Secret"})

        app = Starlette(routes=[Route("/api/retrieve", retrieve)])
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            inject_paths=[r"/api/retrieve"],
        )

        client = TestClient(app)
        response = client.get("/api/retrieve")

        # Should still work with default session
        assert "x-canary-token" in response.headers

    def test_inject_path_modifies_response(self):
        """JSON response body gets canary on inject paths."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        async def retrieve(request):
            return JSONResponse({"documents": ["Doc A", "Doc B"]})

        app = Starlette(routes=[Route("/api/retrieve", retrieve)])
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            inject_paths=[r"/api/retrieve"],
        )

        client = TestClient(app)
        response = client.get("/api/retrieve")

        data = response.json()
        # Verify tokens were injected into string values
        assert "[" in data["documents"][0] and "]" in data["documents"][0]
        assert "[" in data["documents"][1] and "]" in data["documents"][1]

    def test_scan_path_blocks_leaked_response(self):
        """403 returned when generation response contains token."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        middleware_instance = CanaryMiddleware()

        async def retrieve(request):
            return JSONResponse({"doc": "Secret"})

        async def generate(request):
            # Get the token from the middleware
            token = middleware_instance._active_tokens.get("test_session", [""])[0]
            return JSONResponse({"response": f"Leaked: {token}"})

        app = Starlette(
            routes=[
                Route("/api/retrieve", retrieve),
                Route("/api/generate", generate),
            ]
        )
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            middleware=middleware_instance,
            inject_paths=[r"/api/retrieve"],
            scan_paths=[r"/api/generate"],
        )

        client = TestClient(app)

        # First inject tokens
        client.get("/api/retrieve", headers={"X-Session-ID": "test_session"})

        # Then try to leak
        response = client.get("/api/generate", headers={"X-Session-ID": "test_session"})

        assert response.status_code == 403
        assert "Security violation" in response.json()["error"]

    def test_scan_path_allows_safe_response(self):
        """Clean response passes through."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        async def retrieve(request):
            return JSONResponse({"doc": "Secret"})

        async def generate(request):
            return JSONResponse({"response": "Safe summary"})

        app = Starlette(
            routes=[
                Route("/api/retrieve", retrieve),
                Route("/api/generate", generate),
            ]
        )
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            inject_paths=[r"/api/retrieve"],
            scan_paths=[r"/api/generate"],
        )

        client = TestClient(app)

        # Inject tokens
        client.get("/api/retrieve", headers={"X-Session-ID": "test_session"})

        # Safe generation
        response = client.get("/api/generate", headers={"X-Session-ID": "test_session"})

        assert response.status_code == 200
        assert response.json() == {"response": "Safe summary"}

    def test_custom_session_header(self):
        """session_header param changes header name."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        async def retrieve(request):
            return JSONResponse({"doc": "Secret"})

        app = Starlette(routes=[Route("/api/retrieve", retrieve)])
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            inject_paths=[r"/api/retrieve"],
            session_header="X-Custom-Session",
        )

        client = TestClient(app)
        response = client.get("/api/retrieve", headers={"X-Custom-Session": "custom"})

        assert "x-canary-token" in response.headers

    def test_non_json_inject_passthrough(self):
        """Non-JSON retrieval responses pass through unchanged."""
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        async def retrieve(request):
            return PlainTextResponse("Plain text response")

        app = Starlette(routes=[Route("/api/retrieve", retrieve)])
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            inject_paths=[r"/api/retrieve"],
        )

        client = TestClient(app)
        response = client.get("/api/retrieve")

        # Should pass through unchanged
        assert response.status_code == 200
        assert response.text == "Plain text response"

    @pytest.mark.asyncio
    async def test_read_response_body_fallback_no_iterator(self):
        """_read_response_body fallback when body_iterator is missing."""
        from starlette.responses import Response

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        # Create a dummy app
        middleware = RAGuardFastAPIMiddleware(app=None)

        # Plain Response does not have body_iterator unless processed by middleware
        res = Response(content=b"Direct body")
        if hasattr(res, "body_iterator"):
            delattr(res, "body_iterator")  # Force missing body_iterator

        body = await middleware._read_response_body(res)
        assert body == b"Direct body"

    def test_inject_into_list_response(self):
        """JSON response with list root gets canary injected."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        async def retrieve(request):
            return JSONResponse([{"text": "Doc A"}, {"text": "Doc B"}, "plain string"])

        app = Starlette(routes=[Route("/api/retrieve", retrieve)])
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            inject_paths=[r"/api/retrieve"],
        )

        client = TestClient(app)
        response = client.get("/api/retrieve")

        data = response.json()
        assert "[" in data[0]["text"] and "]" in data[0]["text"]
        assert "[" in data[1]["text"] and "]" in data[1]["text"]
        assert "[" in data[2] and "]" in data[2]  # String in list now gets token

    def test_inject_into_nested_json(self):
        """Canary is injected recursively into nested JSON objects."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        async def retrieve(request):
            return JSONResponse(
                {
                    "outer": {
                        "inner_str": "Secret data",
                        "inner_list": ["List item", {"deep_dict": "Deep value"}],
                    }
                }
            )

        app = Starlette(routes=[Route("/api/retrieve", retrieve)])
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            inject_paths=[r"/api/retrieve"],
        )

        client = TestClient(app)
        response = client.get("/api/retrieve")

        data = response.json()
        assert "[" in data["outer"]["inner_str"]
        assert "[" in data["outer"]["inner_list"][0]
        assert "[" in data["outer"]["inner_list"][1]["deep_dict"]


# ============================================================================
# TestFastAPIStreamingAdapter
# ============================================================================


class TestFastAPIStreamingAdapter:
    """Tests for streaming-aware response scanning in FastAPI middleware."""

    def test_streaming_safe_passthrough(self):
        """Safe SSE streaming response passes through all chunks."""
        from starlette.applications import Starlette
        from starlette.responses import StreamingResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        middleware_instance = CanaryMiddleware()

        async def retrieve(request):
            from starlette.responses import JSONResponse

            return JSONResponse({"doc": "Secret"})

        async def generate(request):
            async def stream():
                yield "data: chunk1\n\n"
                yield "data: chunk2\n\n"
                yield "data: chunk3\n\n"

            return StreamingResponse(stream(), media_type="text/event-stream")

        app = Starlette(
            routes=[
                Route("/api/retrieve", retrieve),
                Route("/api/generate", generate),
            ]
        )
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            middleware=middleware_instance,
            inject_paths=[r"/api/retrieve"],
            scan_paths=[r"/api/generate"],
        )

        client = TestClient(app)

        # Inject tokens
        client.get("/api/retrieve", headers={"X-Session-ID": "stream_safe"})

        # Stream safe response
        response = client.get(
            "/api/generate", headers={"X-Session-ID": "stream_safe"}
        )

        assert response.status_code == 200
        assert "chunk1" in response.text
        assert "chunk2" in response.text
        assert "chunk3" in response.text

    def test_streaming_detects_token_mid_stream(self):
        """Streaming response terminated when token detected in a chunk."""
        from starlette.applications import Starlette
        from starlette.responses import StreamingResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        middleware_instance = CanaryMiddleware()

        async def retrieve(request):
            from starlette.responses import JSONResponse

            return JSONResponse({"doc": "Secret"})

        async def generate(request):
            # Get the token from the middleware
            tokens = middleware_instance._store.get_tokens("stream_leak")

            async def stream():
                yield "data: safe chunk\n\n"
                if tokens:
                    yield f"data: leaked {tokens[0]}\n\n"
                yield "data: should not appear\n\n"

            return StreamingResponse(stream(), media_type="text/event-stream")

        app = Starlette(
            routes=[
                Route("/api/retrieve", retrieve),
                Route("/api/generate", generate),
            ]
        )
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            middleware=middleware_instance,
            inject_paths=[r"/api/retrieve"],
            scan_paths=[r"/api/generate"],
        )

        client = TestClient(app)

        # Inject tokens
        client.get("/api/retrieve", headers={"X-Session-ID": "stream_leak"})

        # Stream leaked response
        response = client.get(
            "/api/generate", headers={"X-Session-ID": "stream_leak"}
        )

        assert "Security violation" in response.text
        assert "should not appear" not in response.text

    def test_streaming_detects_token_across_chunk_boundary(self):
        """Token split across two chunks is detected by the sliding window."""
        from starlette.applications import Starlette
        from starlette.responses import StreamingResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        middleware_instance = CanaryMiddleware()

        async def retrieve(request):
            from starlette.responses import JSONResponse

            return JSONResponse({"doc": "Secret"})

        async def generate(request):
            tokens = middleware_instance._store.get_tokens("stream_boundary")

            async def stream():
                if tokens:
                    token = tokens[0]
                    mid = len(token) // 2
                    # Split token across two chunks
                    yield f"data: prefix{token[:mid]}"
                    yield f"{token[mid:]}suffix\n\n"
                yield "data: tail\n\n"

            return StreamingResponse(stream(), media_type="text/event-stream")

        app = Starlette(
            routes=[
                Route("/api/retrieve", retrieve),
                Route("/api/generate", generate),
            ]
        )
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            middleware=middleware_instance,
            inject_paths=[r"/api/retrieve"],
            scan_paths=[r"/api/generate"],
        )

        client = TestClient(app)

        # Inject tokens
        client.get("/api/retrieve", headers={"X-Session-ID": "stream_boundary"})

        # Stream with token split across chunks
        response = client.get(
            "/api/generate", headers={"X-Session-ID": "stream_boundary"}
        )

        assert "Security violation" in response.text

    def test_streaming_fallback_with_decode_response(self):
        """With decode_response=True, streaming falls back to full-buffer scan."""
        from starlette.applications import Starlette
        from starlette.responses import StreamingResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.raguard.adapters.fastapi import RAGuardFastAPIMiddleware

        middleware_instance = CanaryMiddleware(decode_response=True)

        async def retrieve(request):
            from starlette.responses import JSONResponse

            return JSONResponse({"doc": "Secret"})

        async def generate(request):
            async def stream():
                yield "data: safe chunk\n\n"

            return StreamingResponse(stream(), media_type="text/event-stream")

        app = Starlette(
            routes=[
                Route("/api/retrieve", retrieve),
                Route("/api/generate", generate),
            ]
        )
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            middleware=middleware_instance,
            inject_paths=[r"/api/retrieve"],
            scan_paths=[r"/api/generate"],
        )

        client = TestClient(app)

        # Inject tokens
        client.get("/api/retrieve", headers={"X-Session-ID": "stream_decode"})

        # With decode_response=True, should still work (full-buffer fallback)
        response = client.get(
            "/api/generate", headers={"X-Session-ID": "stream_decode"}
        )

        # Safe content should pass through
        assert response.status_code == 200
