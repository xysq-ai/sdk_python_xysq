"""Synchronous client for the xysq SDK.

Manages a background event loop on a daemon thread. Each sync call
dispatches to async via ``loop.run_coroutine_threadsafe().result()``.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from xysq._client import AsyncXysq
from xysq._team import TeamScope
from xysq.knowledge import KnowledgeNamespace
from xysq.memory import MemoryNamespace
from xysq.types import CaptureResult, KnowledgeSource, MemoryItem, SynthesizeResult


def _start_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Run an event loop forever on a daemon thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


class _SyncMemory:
    """Sync wrapper around MemoryNamespace."""

    def __init__(self, ns: MemoryNamespace, loop: asyncio.AbstractEventLoop) -> None:
        self._ns = ns
        self._loop = loop

    def _run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def capture(
        self,
        content: str,
        context: str | None = None,
        tags: list[str] | None = None,
        significance: str = "normal",
        scope: str = "permanent",
        memory_type: str | None = None,
        document_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> CaptureResult:
        return self._run(
            self._ns.capture(
                content,
                context=context,
                tags=tags,
                significance=significance,
                scope=scope,
                memory_type=memory_type,
                document_id=document_id,
                metadata=metadata,
                timestamp=timestamp,
            )
        )

    def surface(
        self,
        query: str,
        budget: str = "mid",
        types: list[str] | None = None,
        intent: str | None = None,
        domain: str | None = None,
        scope: str | None = None,
        memory_type: str | None = None,
        agent_filter: str | None = None,
    ) -> list[MemoryItem]:
        return self._run(
            self._ns.surface(
                query,
                budget=budget,
                types=types,
                intent=intent,
                domain=domain,
                scope=scope,
                memory_type=memory_type,
                agent_filter=agent_filter,
            )
        )

    def synthesize(
        self,
        query: str,
        budget: str = "mid",
        response_schema: dict[str, Any] | None = None,
        write_back: bool = False,
    ) -> SynthesizeResult:
        return self._run(
            self._ns.synthesize(
                query,
                budget=budget,
                response_schema=response_schema,
                write_back=write_back,
            )
        )

    def list(
        self,
        limit: int = 20,
        agent_filter: str | None = None,
    ) -> list[MemoryItem]:
        return self._run(self._ns.list(limit=limit, agent_filter=agent_filter))

    def delete(self, memory_id: str) -> dict:
        return self._run(self._ns.delete(memory_id))


class _SyncKnowledge:
    """Sync wrapper around KnowledgeNamespace."""

    def __init__(self, ns: KnowledgeNamespace, loop: asyncio.AbstractEventLoop) -> None:
        self._ns = ns
        self._loop = loop

    def _run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def add(
        self,
        type: str,
        content: str | None = None,
        url: str | None = None,
        title: str | None = None,
        location: str | None = None,
        session_context: str | None = None,
        confidence: str = "medium",
    ) -> KnowledgeSource:
        return self._run(
            self._ns.add(
                type,
                content=content,
                url=url,
                title=title,
                location=location,
                session_context=session_context,
                confidence=confidence,
            )
        )

    def list(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        type: str | None = None,
    ) -> list[KnowledgeSource]:
        return self._run(
            self._ns.list(limit=limit, offset=offset, status=status, type=type)
        )


class _SyncTeamScope:
    """Sync wrapper around TeamScope."""

    def __init__(self, team_scope: TeamScope, loop: asyncio.AbstractEventLoop) -> None:
        self.memory = _SyncMemory(team_scope.memory, loop)
        self.knowledge = _SyncKnowledge(team_scope.knowledge, loop)


class Xysq:
    """Synchronous client for the xysq memory API.

    Usage::

        with Xysq(api_key="xysq_...") as client:
            memories = client.memory.surface("user preferences")
            client.memory.capture("User prefers dark mode")

    Or without a context manager::

        client = Xysq(api_key="xysq_...")
        memories = client.memory.surface("user preferences")
        client.close()
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=_start_loop, args=(self._loop,), daemon=True
        )
        self._thread.start()

        self._async_client = AsyncXysq(
            api_key=api_key, timeout=timeout, max_retries=max_retries
        )
        self.memory = _SyncMemory(self._async_client.memory, self._loop)
        self.knowledge = _SyncKnowledge(self._async_client.knowledge, self._loop)

    def team(self, team_id: str) -> _SyncTeamScope:
        """Return a team-scoped view with auto team_id injection."""
        async_scope = self._async_client.team(team_id)
        return _SyncTeamScope(async_scope, self._loop)

    def close(self) -> None:
        """Close the client and shut down the background event loop."""
        asyncio.run_coroutine_threadsafe(
            self._async_client.aclose(), self._loop
        ).result()
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

    def __enter__(self) -> Xysq:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
