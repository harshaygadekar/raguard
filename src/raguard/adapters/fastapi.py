"""FastAPI adapter for RAGuard.

Provides a BaseHTTPMiddleware that injects canary tokens into retrieval
responses and scans generation responses for exfiltration.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, cast
from uuid import uuid4

from ..config import RAGuardConfig
from ..core import CanaryMiddleware
from ..exceptions import RAGuardImportError

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response, StreamingResponse
except ImportError as e:
    raise RAGuardImportError("fastapi", "fastapi", "fastapi") from e

logger = logging.getLogger(__name__)


class RAGuardFastAPIMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware for RAG canary token injection and scanning.

    CONFIGURABLE: Specify which paths trigger injection vs scanning.

    Usage:
        app = FastAPI()
        app.add_middleware(
            RAGuardFastAPIMiddleware,
            middleware=CanaryMiddleware(),
            inject_paths=[r"^/api/retrieve"],
            scan_paths=[r"^/api/generate"],
        )
    """

    def __init__(
        self,
        app: Any,
        middleware: CanaryMiddleware | None = None,
        config: RAGuardConfig | None = None,
        inject_paths: list[str] | None = None,
        scan_paths: list[str] | None = None,
        session_header: str = "X-Session-ID",
    ) -> None:
        super().__init__(app)
        self.raguard = middleware or CanaryMiddleware(config=config)
        self.inject_paths = inject_paths or []
        self.scan_paths = scan_paths or []
        self.session_header = session_header

    def _matches_any_path(self, request_path: str, patterns: list[str]) -> bool:
        """Check if request path matches any of the given regex patterns."""
        return any(re.search(pattern, request_path) for pattern in patterns)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process request: inject on retrieval paths, scan on generation paths."""
        session_id = request.headers.get(self.session_header)
        if session_id is None:
            session_id = str(uuid4())
            logger.warning(
                "RAGuard: No session ID header '%s' found; "
                "generated ephemeral session %s",
                self.session_header,
                session_id,
            )
        path = request.url.path

        # --- Retrieval paths: inject canary, add token to response ---
        if self._matches_any_path(path, self.inject_paths):
            response = await call_next(request)
            return await self._handle_inject_response(
                cast(Response, response), session_id
            )

        # --- Generation paths: scan output for leaked tokens ---
        if self._matches_any_path(path, self.scan_paths):
            response = await call_next(request)
            return await self._handle_scan_response(
                cast(Response, response), session_id
            )

        # --- Non-configured paths: pass through ---
        response = await call_next(request)
        return cast(Response, response)

    async def _handle_inject_response(
        self, response: Response, session_id: str
    ) -> Response:
        """For retrieval endpoints: inject canary token and expose it.

        Reads the JSON response body, injects a canary token, and adds
        the token value in an X-Canary-Token response header so the
        calling application can include it in the LLM context.
        """
        body = b""
        try:
            body = await self._read_response_body(response)
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            # Non-JSON response — can't inject, pass through
            return self._rebuild_response(response, body)

        # Generate token for this session
        token = self.raguard.generate_token(session_id)

        # Append token to string values in the response
        # Works with: {"documents": ["text1", "text2"]}
        # or: {"chunks": [{"text": "..."}], "results": [...]}
        if isinstance(data, dict):
            self._inject_into_json(data, token)
        elif isinstance(data, list):
            self._inject_into_list(data, token)

        modified_body = json.dumps(data).encode("utf-8")
        headers = dict(response.headers)
        headers["x-canary-token"] = token  # Expose token to caller
        # Remove content-length since body size changed
        headers.pop("content-length", None)

        return Response(
            content=modified_body,
            status_code=response.status_code,
            headers=headers,
            media_type="application/json",
        )

    _MAX_INJECT_DEPTH = 20

    def _inject_into_json(
        self, obj: dict[str, Any], token: str, depth: int = 0
    ) -> None:
        """Recursively append canary token to string values in a dict."""
        if depth >= self._MAX_INJECT_DEPTH:
            return
        for key, value in obj.items():
            if isinstance(value, str):
                obj[key] = f"{value}\n\n[{token}]"
            elif isinstance(value, dict):
                self._inject_into_json(value, token, depth + 1)
            elif isinstance(value, list):
                self._inject_into_list(value, token, depth + 1)

    def _inject_into_list(
        self, lst: list[Any], token: str, depth: int = 0
    ) -> None:
        """Recursively append canary token to string values in a list."""
        if depth >= self._MAX_INJECT_DEPTH:
            return
        for i, item in enumerate(lst):
            if isinstance(item, str):
                lst[i] = f"{item}\n\n[{token}]"
            elif isinstance(item, dict):
                self._inject_into_json(item, token, depth + 1)
            elif isinstance(item, list):
                self._inject_into_list(item, token, depth + 1)

    async def _handle_scan_response(
        self, response: Response, session_id: str
    ) -> Response:
        """For generation endpoints: scan response for leaked canary tokens.

        If the response is a StreamingResponse and decode_response is disabled,
        uses a sliding-window scanner that forwards chunks as they arrive.
        Otherwise, falls back to full-buffer scanning.
        """
        body_iterator = getattr(response, "body_iterator", None)
        content_type = response.headers.get("content-type", "")
        is_streaming = body_iterator is not None and "text/event-stream" in content_type

        # Streaming scan: only when streaming AND decode_response is off
        # (decode transforms require the full response text)
        if is_streaming and not self.raguard.config.decode_response:
            return await self._handle_streaming_scan(response, session_id)

        # Non-streaming (or decode_response enabled): full-buffer scan
        body = await self._read_response_body(response)

        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            return self._rebuild_response(response, body)

        is_safe = await self.raguard.is_safe_async(text, session_id)

        if not is_safe:
            logger.warning(
                "RAGuard: Blocked response for session '%s' — canary token detected",
                session_id,
            )
            # Clean up session after detection
            self.raguard.clear_session(session_id)
            return JSONResponse(
                status_code=403,
                content={"error": "Security violation: response blocked"},
            )

        # Clean up session after successful scan
        self.raguard.clear_session(session_id)
        return self._rebuild_response(response, body)

    async def _handle_streaming_scan(
        self, response: Response, session_id: str
    ) -> Response:
        """Scan a streaming response using a sliding window.

        Forwards chunks to the client as they arrive. Maintains a buffer
        of the last ``max_token_len`` characters to catch tokens that span
        chunk boundaries. If a token is detected, terminates the stream
        with an error event.
        """
        body_iterator = getattr(response, "body_iterator", None)
        if body_iterator is None:
            return response

        tokens = self.raguard._store.get_tokens(session_id)
        if not tokens:
            # No tokens to scan for — pass through
            self.raguard.clear_session(session_id)
            return response

        max_token_len = max(len(t) for t in tokens)

        async def _scanning_generator() -> Any:
            buffer = ""
            detected = False

            async for raw_chunk in body_iterator:
                if isinstance(raw_chunk, bytes):
                    chunk_str = raw_chunk.decode("utf-8", errors="ignore")
                elif isinstance(raw_chunk, str):
                    chunk_str = raw_chunk
                else:
                    chunk_str = bytes(raw_chunk).decode("utf-8", errors="ignore")

                # Combine buffer overlap with current chunk for scanning
                scan_window = buffer + chunk_str

                for token in tokens:
                    if token in scan_window:
                        detected = True
                        break

                if detected:
                    logger.warning(
                        "RAGuard: Blocked streaming response for session '%s' "
                        "— canary token detected mid-stream",
                        session_id,
                    )
                    self.raguard._metrics.record_scan_blocked()
                    # Emit error event and terminate stream
                    error_msg = "Security violation: response blocked"
                    yield f'\ndata: {{"error": "{error_msg}"}}\n\n'
                    self.raguard.clear_session(session_id)
                    return

                # Yield the chunk to the client
                yield raw_chunk

                # Keep trailing characters for cross-boundary detection
                if max_token_len > 1:
                    buffer = chunk_str[-(max_token_len - 1) :]
                else:
                    buffer = ""

            # Stream completed without detection
            if not detected:
                self.raguard._metrics.record_scan_safe()
            self.raguard.clear_session(session_id)

        return StreamingResponse(
            _scanning_generator(),
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    async def _read_response_body(self, response: Response) -> bytes:
        """Read response body as bytes, handling StreamingResponse."""
        body_iterator = getattr(response, "body_iterator", None)
        if body_iterator is None:
            body = getattr(response, "body", b"")
            return cast(bytes, body)
        body_chunks: list[bytes] = []
        async for chunk in body_iterator:
            if isinstance(chunk, str):
                body_chunks.append(chunk.encode("utf-8"))
            else:
                body_chunks.append(chunk)
        return b"".join(body_chunks)

    def _rebuild_response(self, response: Response, body: bytes) -> Response:
        """Rebuild a Response from consumed body bytes."""
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
