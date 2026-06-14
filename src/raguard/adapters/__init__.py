"""Framework adapters for RAGuard.

Each adapter requires its respective optional dependency:
    pip install "raguard[langchain]"
    pip install "raguard[llamaindex]"
    pip install "raguard[fastapi]"
"""

from __future__ import annotations

from typing import Any

__all__: list[str] = []


def __getattr__(name: str) -> Any:
    """Lazy-load adapters to avoid importing optional dependencies at
    package level. Each adapter module raises RAGuardImportError on import
    if its dependency is missing.
    """
    _adapter_map = {
        "RAGuardLangChainCallback": "langchain",
        "RAGuardLlamaIndexPostprocessor": "llamaindex",
        "RAGuardFastAPIMiddleware": "fastapi",
    }
    if name in _adapter_map:
        import importlib

        module = importlib.import_module(f".{_adapter_map[name]}", package=__name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
