"""LlamaIndex adapter for RAGuard.

Provides a NodePostprocessor that injects canary tokens into retrieved
nodes before they reach the LLM.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict

from ..config import RAGuardConfig
from ..core import CanaryMiddleware
from ..exceptions import RAGuardImportError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from llama_index.core.postprocessor.types import BaseNodePostprocessor

    _LLAMAINDEX_AVAILABLE = True
else:
    try:
        from llama_index.core.postprocessor.types import BaseNodePostprocessor

        _LLAMAINDEX_AVAILABLE = True
    except ImportError:
        _LLAMAINDEX_AVAILABLE = False

        class BaseNodePostprocessor:
            pass


class RAGuardLlamaIndexPostprocessor(BaseNodePostprocessor):
    """LlamaIndex node postprocessor that injects canary tokens into
    retrieved nodes before they reach the LLM.

    Usage:
        postprocessor = RAGuardLlamaIndexPostprocessor(session_id="user_123")
        safe_nodes = postprocessor.postprocess_nodes(nodes, query_bundle)

        # After generation, manually scan the response:
        response = query_engine.query("What is the secret?")
        if not postprocessor.scan_response(str(response)):
            raise CanaryTokenDetected(session_id=postprocessor.session_id)
    """

    session_id: str
    middleware: CanaryMiddleware

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        session_id: str,
        middleware: CanaryMiddleware | None = None,
        config: RAGuardConfig | None = None,
        **kwargs: Any,
    ) -> None:
        if not _LLAMAINDEX_AVAILABLE:
            raise RAGuardImportError("llamaindex", "llama-index-core", "llamaindex")
        super().__init__(  # type: ignore[call-arg]
            session_id=session_id,
            middleware=middleware or CanaryMiddleware(config=config),
            **kwargs,
        )

    def _postprocess_nodes(
        self,
        nodes: list[Any],
        query_bundle: Any | None = None,
    ) -> list[Any]:
        """Inject canary token into each node's text content."""
        texts = [node.node.get_content() for node in nodes]
        injected = self.middleware.inject(texts, self.session_id)

        if isinstance(injected, list):
            for node_with_score, injected_text in zip(nodes, injected, strict=False):
                node_with_score.node.set_content(injected_text)
        else:
            nodes[0].node.set_content(injected)

        return nodes

    def scan_response(self, response_text: str) -> bool:
        """Scan an LLM response for canary token leakage.

        Returns:
            True if the response is safe, False if canary token was detected.
        """
        return self.middleware.is_safe(response_text, self.session_id)
