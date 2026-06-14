"""RAGuard: Deterministic security middleware for RAG applications."""

from .config import RAGuardConfig
from .core import CanaryMiddleware
from .exceptions import CanaryTokenDetected
from .metrics import RAGuardMetrics
from .store import InMemoryTokenStore, TokenStore


def __getattr__(name: str) -> type:
    if name == "RedisTokenStore":
        from .redis_store import RedisTokenStore

        return RedisTokenStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__version__ = "0.1.0"
__all__ = [
    "CanaryMiddleware",
    "RAGuardConfig",
    "CanaryTokenDetected",
    "RAGuardMetrics",
    "TokenStore",
    "InMemoryTokenStore",
    "RedisTokenStore",
]
