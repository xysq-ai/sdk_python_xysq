"""Async client for the xysq SDK."""

from __future__ import annotations

from xysq._config import resolve_api_key, resolve_base_url
from xysq._http import AsyncHTTPClient
from xysq._team import TeamScope
from xysq.knowledge import KnowledgeNamespace
from xysq.memory import MemoryNamespace


class AsyncXysq:
    """Async client for the xysq memory API.

    Usage::

        async with AsyncXysq(api_key="xysq_...") as client:
            memories = await client.memory.surface("user preferences")
            await client.memory.capture("User prefers dark mode")

    Or without a context manager::

        client = AsyncXysq(api_key="xysq_...")
        memories = await client.memory.surface("user preferences")
        await client.aclose()
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        key = resolve_api_key(api_key)
        base_url = resolve_base_url()
        self._http = AsyncHTTPClient(
            api_key=key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.memory = MemoryNamespace(self._http)
        self.knowledge = KnowledgeNamespace(self._http)

    def team(self, team_id: str) -> TeamScope:
        """Return a team-scoped view with auto team_id injection."""
        return TeamScope(self._http, team_id=team_id)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncXysq:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
