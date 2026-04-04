from xysq._http import AsyncHTTPClient
from xysq.memory import MemoryNamespace

_DEFAULT_BASE_URL = "https://api.xysq.ai"


class XysqClient:
    """
    Async client for the xysq memory API.

    Usage::

        client = XysqClient(api_key="xysq_...")
        memories = await client.memory.recall("user preferences")
        await client.memory.retain("User prefers dark mode")
        await client.aclose()

    Or as an async context manager::

        async with XysqClient(api_key="xysq_...") as client:
            memories = await client.memory.recall("user preferences")
    """

    def __init__(self, api_key: str, base_url: str = _DEFAULT_BASE_URL) -> None:
        self._http = AsyncHTTPClient(api_key=api_key, base_url=base_url)
        self.memory = MemoryNamespace(self._http)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "XysqClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
