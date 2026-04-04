class XysqError(Exception):
    """Base exception for all xysq SDK errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthError(XysqError):
    """Raised when the API key is invalid or missing (HTTP 401)."""


class QuotaError(XysqError):
    """Raised when the user's memory limit has been reached (HTTP 429)."""


class NotFoundError(XysqError):
    """Raised when a requested resource does not exist (HTTP 404)."""
