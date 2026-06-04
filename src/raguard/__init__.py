"""RAGuard: Deterministic security middleware for RAG applications."""

from .core import CanaryMiddleware
from .config import RAGuardConfig

__version__ = "0.1.0"
__all__ = ["CanaryMiddleware", "RAGuardConfig"]