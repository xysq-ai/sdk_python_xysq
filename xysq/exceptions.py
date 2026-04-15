"""Exception hierarchy for the xysq SDK."""


class XysqError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthError(XysqError):
    """401 or missing API key."""


class NotFoundError(XysqError):
    """404."""


class QuotaError(XysqError):
    """429 rate limit/quota."""


class TimeoutError(XysqError):
    """Request timed out."""


class RetryError(XysqError):
    """All retries exhausted."""
