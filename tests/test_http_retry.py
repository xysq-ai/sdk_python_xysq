"""The HTTP retry policy applies identically to GET and POST -- both go through
one _request loop, so 429 -> QuotaError and Retry-After honoring can't drift
per verb (the review-found bug: get() used to raise RetryError, not QuotaError,
and ignored Retry-After)."""
from __future__ import annotations

import httpx
import pytest

from xysq._http import AsyncHTTPClient
from xysq.exceptions import QuotaError


def _client_with(transport: httpx.MockTransport, max_retries: int = 1) -> AsyncHTTPClient:
    c = AsyncHTTPClient(api_key="xysq_test", base_url="https://api.test", max_retries=max_retries)
    # swap in the mock transport, keep the configured headers/base_url
    c._client = httpx.AsyncClient(base_url="https://api.test", transport=transport)
    return c


@pytest.mark.asyncio
async def test_get_raises_quota_error_on_persistent_429():
    """A GET that keeps 429ing must exhaust retries into QuotaError, not a
    generic RetryError (matches post())."""
    handler = lambda req: httpx.Response(429, text="slow down")  # noqa: E731
    c = _client_with(httpx.MockTransport(handler), max_retries=1)
    try:
        with pytest.raises(QuotaError):
            await c.get("/sdk/vaults")
    finally:
        await c.aclose()


@pytest.mark.asyncio
async def test_post_raises_quota_error_on_persistent_429():
    """The mirror -- POST behaves the same (regression guard for the shared loop)."""
    handler = lambda req: httpx.Response(429, text="slow down")  # noqa: E731
    c = _client_with(httpx.MockTransport(handler), max_retries=1)
    try:
        with pytest.raises(QuotaError):
            await c.post("/sdk/vaults/x/push", json={"content": "y"})
    finally:
        await c.aclose()


@pytest.mark.asyncio
async def test_get_returns_body_on_200():
    handler = lambda req: httpx.Response(200, json={"items": [{"vault_id": "v", "name": "n"}]})  # noqa: E731
    c = _client_with(httpx.MockTransport(handler))
    try:
        data = await c.get("/sdk/vaults")
        assert data["items"][0]["vault_id"] == "v"
    finally:
        await c.aclose()
