"""Internal HTTP client — wraps httpx, injects auth, maps errors."""

from typing import Any

import httpx

from xysq.exceptions import AuthError, NotFoundError, QuotaError, XysqError

_DEFAULT_BASE_URL = "https://api.xysq.ai"


class AsyncHTTPClient:
    def __init__(self, api_key: str, base_url: str = _DEFAULT_BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    async def get(self, path: str, **params: Any) -> Any:
        resp = await self._client.get(path, params=params or None)
        return self._check(resp)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        resp = await self._client.post(path, json=json)
        return self._check(resp)

    async def delete(self, path: str) -> Any:
        resp = await self._client.delete(path)
        return self._check(resp)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncHTTPClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    @staticmethod
    def _check(resp: httpx.Response) -> Any:
        if resp.status_code == 401:
            raise AuthError(resp.text, status_code=401)
        if resp.status_code == 404:
            raise NotFoundError(resp.text, status_code=404)
        if resp.status_code == 429:
            raise QuotaError(resp.text, status_code=429)
        if resp.is_error:
            raise XysqError(resp.text, status_code=resp.status_code)
        return resp.json()
