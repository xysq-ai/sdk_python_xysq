"""Config resolution — reads from constructor params and environment."""

import os

_DEFAULT_BASE_URL = "https://api.xysq.ai"


def resolve_api_key(api_key: str | None) -> str:
    key = api_key or os.environ.get("XYSQ_API_KEY")
    if not key:
        from xysq.exceptions import AuthError

        raise AuthError(
            "No API key provided. Pass api_key= or set XYSQ_API_KEY environment variable.",
            status_code=401,
        )
    return key


def resolve_base_url() -> str:
    return os.environ.get("XYSQ_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
