"""LangChain adapter for RAGuard.

Provides a BaseCallbackHandler that injects canary tokens on retrieval
and scans LLM output for exfiltration.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any
from uuid import UUID

from ..config import RAGuardConfig
from ..core import CanaryMiddleware
from ..exceptions import CanaryTokenDetected, RAGuardImportError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.documents import Document
    from langchain_core.outputs import LLMResult

    _LANGCHAIN_AVAILABLE = True
else:
    try:
        from langchain_core.callbacks.base import BaseCallbackHandler
        from langchain_core.documents import Document
        from langchain_core.outputs import LLMResult

        _LANGCHAIN_AVAILABLE = True
    except ImportError:
        try:
            from langchain.callbacks.base import BaseCallbackHandler
            from langchain.docstore.document import Document
            from langchain.schema import LLMResult

            _LANGCHAIN_AVAILABLE = True
        except ImportError:
            _LANGCHAIN_AVAILABLE = False

            class BaseCallbackHandler:
                pass


class RAGuardLangChainCallback(BaseCallbackHandler):
    """LangChain callback handler that injects canary tokens on retrieval
    and scans LLM output for exfiltration.

    Usage:
        canary_cb = RAGuardLangChainCallback(session_id="user_123")
        chain = RetrievalQA.from_chain_id(
            llm=ChatOpenAI(callbacks=[canary_cb]),
            retriever=retriever,
        )
    """

    def __init__(
        self,
        session_id: str,
        middleware: CanaryMiddleware | None = None,
        config: RAGuardConfig | None = None,
        **kwargs: Any,
    ) -> None:
        if not _LANGCHAIN_AVAILABLE:
            raise RAGuardImportError("langchain", "langchain", "langchain")
        super().__init__(**kwargs)
        self.session_id = session_id
        self.middleware = middleware or CanaryMiddleware(config=config)

    def on_retriever_end(
        self,
        documents: Sequence[Document],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Inject canary token into each retrieved Document's page_content."""
        texts = [doc.page_content for doc in documents]
        injected = self.middleware.inject(texts, self.session_id)

        if isinstance(injected, list):
            for doc, injected_text in zip(documents, injected, strict=False):
                doc.page_content = injected_text
        else:
            documents[0].page_content = injected

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Scan all LLM generations for canary token leakage."""
        for generation_list in response.generations:
            for generation in generation_list:
                if not self.middleware.is_safe(generation.text, self.session_id):
                    raise CanaryTokenDetected(session_id=self.session_id)

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Scan chain outputs for canary token leakage.

        After scanning, clears the session's tokens to prevent memory
        accumulation in long-running services.
        """
        try:
            for key in ["answer", "result", "output", "text"]:
                if key in outputs and isinstance(outputs[key], str):
                    if not self.middleware.is_safe(outputs[key], self.session_id):
                        raise CanaryTokenDetected(session_id=self.session_id)
        finally:
            self.middleware.clear_session(self.session_id)

