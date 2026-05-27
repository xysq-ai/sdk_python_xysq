"""Synchronous client for the xysq SDK.

Manages a background event loop on a daemon thread. Each sync call
dispatches to async via ``loop.run_coroutine_threadsafe().result()``.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import os

from xysq._client import AsyncXysq
from xysq._team import TeamScope
from xysq.memory import MemoryNamespace
from xysq.organise import OrganiseNamespace
from xysq.types import (
    CaptureResult,
    FileStatus,
    Folder,
    MemoryItem,
    OrganiseFile,
    StatusResult,
    SynthesizeResult,
)


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
        mood: str | None = None,
        scope: str | None = None,
        agent_filter: str | None = None,
    ) -> list[MemoryItem]:
        return self._run(
            self._ns.surface(
                query,
                budget=budget,
                types=types,
                intent=intent,
                domain=domain,
                mood=mood,
                scope=scope,
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

    def delete(self, document_id: str) -> dict:
        return self._run(self._ns.delete(document_id))

    def tags(self) -> dict:
        return self._run(self._ns.tags())

    def status(self, document_id: str) -> StatusResult:
        return self._run(self._ns.status(document_id))

    def wait(self, document_id: str, timeout: float = 30.0, interval: float = 0.5) -> StatusResult:
        return self._run(self._ns.wait(document_id, timeout=timeout, interval=interval))


class _SyncOrganise:
    """Sync wrapper around OrganiseNamespace."""

    def __init__(
        self, ns: OrganiseNamespace, loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._ns = ns
        self._loop = loop

    def _run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def list_folders(self) -> list[Folder]:
        return self._run(self._ns.list_folders())

    def get_folder(self, folder_id: str) -> tuple[Folder, list[Folder]]:
        return self._run(self._ns.get_folder(folder_id))

    def create_folder(
        self, name: str, parent_id: str | None = None,
    ) -> Folder:
        return self._run(self._ns.create_folder(name, parent_id=parent_id))

    def rename_folder(self, folder_id: str, name: str) -> None:
        return self._run(self._ns.rename_folder(folder_id, name))

    def move_folder(self, folder_id: str, new_parent_id: str) -> None:
        return self._run(self._ns.move_folder(folder_id, new_parent_id))

    def delete_folder(
        self, folder_id: str, forget_memories: bool = False,
    ) -> int:
        return self._run(
            self._ns.delete_folder(folder_id, forget_memories=forget_memories),
        )

    def upload_file(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        content: bytes | str | None = None,
        filename: str | None = None,
        mime_type: str | None = None,
        folder_id: str | None = None,
    ) -> OrganiseFile:
        return self._run(
            self._ns.upload_file(
                path=path,
                content=content,
                filename=filename,
                mime_type=mime_type,
                folder_id=folder_id,
            ),
        )

    def file_status(self, asset_id: str) -> FileStatus:
        return self._run(self._ns.file_status(asset_id))

    def wait_for_file(
        self,
        asset_id: str,
        timeout: float = 60.0,
        interval: float = 1.0,
    ) -> FileStatus:
        return self._run(
            self._ns.wait_for_file(asset_id, timeout=timeout, interval=interval),
        )


class _SyncTeamScope:
    """Sync wrapper around TeamScope."""

    def __init__(self, team_scope: TeamScope, loop: asyncio.AbstractEventLoop) -> None:
        self.memory = _SyncMemory(team_scope.memory, loop)
        self.organise = _SyncOrganise(team_scope.organise, loop)


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
        timeout: float = 60.0,
        max_retries: int = 3,
        agent_name: str | None = None,
    ) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=_start_loop, args=(self._loop,), daemon=True
        )
        self._thread.start()

        self._async_client = AsyncXysq(
            api_key=api_key, timeout=timeout, max_retries=max_retries,
            agent_name=agent_name,
        )
        self.memory = _SyncMemory(self._async_client.memory, self._loop)
        self.organise = _SyncOrganise(self._async_client.organise, self._loop)

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
