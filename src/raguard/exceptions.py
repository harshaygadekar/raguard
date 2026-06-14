"""Custom exceptions for RAGuard."""


class CanaryTokenDetected(Exception):  # noqa: N818
    """Raised when a canary token is detected in LLM output, indicating exfiltration."""

    def __init__(self, session_id: str, message: str | None = None) -> None:
        self.session_id = session_id
        self.message = message or (
            f"Canary token detected in output for session '{session_id}'. "
            "Possible context exfiltration attempt."
        )
        super().__init__(self.message)


class RAGuardImportError(ImportError):
    """Raised when an adapter's optional dependency is not installed."""

    def __init__(self, adapter_name: str, package_name: str, extra_name: str) -> None:
        self.adapter_name = adapter_name
        super().__init__(
            f"The '{adapter_name}' adapter requires the '{package_name}' package. "
            f'Install it with: pip install "raguard[{extra_name}]"'
        )
