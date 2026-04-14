"""Internal HTTP client — async transport with retry, auth, and error mapping."""

from __future__ import annotations

import random
from typing import Any

import httpx

from xysq._log import get_logger
from xysq.exceptions import (
    AuthError,
    NotFoundError,
    QuotaError,
    RetryError,
    TimeoutError,
    XysqError,
)

logger = get_logger("http")

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_BASE_BACKOFF = 0.5
_MAX_BACKOFF = 8.0
_JITTER_FACTOR = 0.25


class AsyncHTTPClient:
    """Async HTTP client with retry, auth header injection, and error mapping.

    All SDK routes are POST, so only a ``post()`` method is exposed.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Send a POST request with automatic retry on transient failures."""
        import asyncio

        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                logger.debug("POST %s (attempt %d)", path, attempt + 1)
                resp = await self._client.post(path, json=json)
            except httpx.TimeoutException as exc:
                logger.warning("Timeout on POST %s (attempt %d)", path, attempt + 1)
                last_exc = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff(attempt))
                    continue
                raise TimeoutError(
                    f"Request to {path} timed out after {self._max_retries + 1} attempts.",
                    status_code=None,
                ) from exc

            if resp.status_code not in _RETRYABLE_STATUS_CODES:
                return self._handle_response(resp)

            # Retryable status — back off and retry
            logger.warning(
                "Retryable %d on POST %s (attempt %d)",
                resp.status_code,
                path,
                attempt + 1,
            )
            last_exc = XysqError(resp.text, status_code=resp.status_code)

            if attempt < self._max_retries:
                delay = self._backoff(attempt)
                # Respect Retry-After header on 429
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after is not None:
                        try:
                            delay = max(delay, float(retry_after))
                        except ValueError:
                            pass
                await asyncio.sleep(delay)
            else:
                # Final attempt exhausted — map the error
                if resp.status_code == 429:
                    raise QuotaError(resp.text, status_code=429)
                raise RetryError(
                    f"All {self._max_retries + 1} attempts failed for POST {path}. "
                    f"Last status: {resp.status_code}.",
                    status_code=resp.status_code,
                ) from last_exc

        # Should not reach here, but satisfy type checkers
        raise RetryError(  # pragma: no cover
            f"All retries exhausted for POST {path}.",
            status_code=None,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncHTTPClient:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _backoff(attempt: int) -> float:
        """Exponential backoff with 25 % jitter, capped at _MAX_BACKOFF."""
        base = min(_BASE_BACKOFF * (2**attempt), _MAX_BACKOFF)
        jitter = base * _JITTER_FACTOR * random.random()  # noqa: S311
        return base + jitter

    @staticmethod
    def _handle_response(resp: httpx.Response) -> Any:
        """Map non-retryable HTTP errors to SDK exceptions."""
        if resp.status_code in (401, 403):
            raise AuthError(resp.text, status_code=resp.status_code)
        if resp.status_code == 404:
            raise NotFoundError(resp.text, status_code=404)
        if resp.status_code == 429:
            raise QuotaError(resp.text, status_code=429)
        if resp.is_error:
            raise XysqError(resp.text, status_code=resp.status_code)
        return resp.json()
