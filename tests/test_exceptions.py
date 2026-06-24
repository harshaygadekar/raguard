"""Unit tests for RAGuard exceptions."""

from src.raguard.exceptions import CanaryTokenDetected, RAGuardImportError


def test_canary_token_detected_message():
    """Default message includes session_id."""
    exc = CanaryTokenDetected(session_id="test_session_123")
    assert "test_session_123" in str(exc)
    assert "Canary token detected" in str(exc)


def test_canary_token_detected_custom_message():
    """Custom message overrides default."""
    exc = CanaryTokenDetected(session_id="test_session", message="Custom error message")
    assert str(exc) == "Custom error message"


def test_canary_token_detected_session_attr():
    """session_id attribute is accessible."""
    exc = CanaryTokenDetected(session_id="my_session")
    assert exc.session_id == "my_session"
    assert isinstance(exc, Exception)


def test_raguard_import_error_message():
    """Error message includes install command."""
    exc = RAGuardImportError(
        adapter_name="langchain", package_name="langchain", extra_name="langchain"
    )
    error_msg = str(exc)
    assert "langchain" in error_msg
    assert "pip install" in error_msg
    assert "raguard-security[langchain]" in error_msg


def test_raguard_import_error_is_import_error():
    """isinstance(exc, ImportError) is True."""
    exc = RAGuardImportError(
        adapter_name="fastapi", package_name="fastapi", extra_name="fastapi"
    )
    assert isinstance(exc, ImportError)
    assert exc.adapter_name == "fastapi"
