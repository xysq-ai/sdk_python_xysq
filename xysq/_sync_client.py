"""Synchronous client for the xysq SDK.

Manages a background event loop on a daemon thread. Each sync call
dispatches to async via ``loop.run_coroutine_threadsafe().result()``.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from xysq._client import AsyncXysq
from xysq.tags import TagsNamespace
from xysq.threads import ThreadsNamespace
from xysq.vaults import VaultsNamespace
from xysq.types import (
    PushResult,
    SourceTagsResult,
    Tag,
    Vault,
    VaultItem,
)


def _start_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Run an event loop forever on a daemon thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


class _SyncThreads:
    """Sync wrapper around ThreadsNamespace (the checkpointer)."""

    def __init__(self, ns: ThreadsNamespace, loop: asyncio.AbstractEventLoop) -> None:
        self._ns = ns
        self._loop = loop

    def _run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def append(self, vault_id: str, thread_id: str, role: str, content: str,
               turn_key: str | None = None) -> Turn:
        return self._run(self._ns.append(vault_id, thread_id, role, content,
                                         turn_key=turn_key))

    def read(self, vault_id: str, thread_id: str, last_n: int | None = None,
             token_budget: int | None = None) -> ThreadWindow:
        return self._run(self._ns.read(vault_id, thread_id, last_n=last_n,
                                       token_budget=token_budget))

    def list(self, vault_id: str) -> list[ThreadInfo]:
        return self._run(self._ns.list(vault_id))

    def flush(self, vault_id: str, thread_id: str) -> int:
        return self._run(self._ns.flush(vault_id, thread_id))

    def clear(self, vault_id: str, thread_id: str) -> int:
        return self._run(self._ns.clear(vault_id, thread_id))


class _SyncTags:
    """Sync wrapper around TagsNamespace (the tag vocabulary)."""

    def __init__(self, ns: TagsNamespace, loop: asyncio.AbstractEventLoop) -> None:
        self._ns = ns
        self._loop = loop

    def _run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def list(self, project_id: str) -> list[Tag]:
        return self._run(self._ns.list(project_id))

    def create(self, project_id: str, name: str) -> Tag:
        return self._run(self._ns.create(project_id, name))

    def rename(self, project_id: str, tag_id: str, name: str) -> Tag:
        return self._run(self._ns.rename(project_id, tag_id, name))

    def delete(self, project_id: str, tag_id: str) -> int:
        return self._run(self._ns.delete(project_id, tag_id))

    def restore(self, project_id: str, tag_id: str) -> bool:
        return self._run(self._ns.restore(project_id, tag_id))

    def apply(self, vault_id: str, source_id: str,
              add: list[str] | None = None,
              remove: list[str] | None = None) -> SourceTagsResult:
        return self._run(self._ns.apply(vault_id, source_id, add=add, remove=remove))


class _SyncVaults:
    """Sync wrapper around VaultsNamespace (the /sdk vault API)."""

    def __init__(self, ns: VaultsNamespace, loop: asyncio.AbstractEventLoop) -> None:
        self._ns = ns
        self._loop = loop

    def _run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def create(self, name: str) -> Vault:
        return self._run(self._ns.create(name))

    def list(self) -> list[Vault]:
        return self._run(self._ns.list())

    def rename(self, vault_id: str, name: str) -> None:
        return self._run(self._ns.rename(vault_id, name))

    def delete(self, vault_id: str) -> None:
        return self._run(self._ns.delete(vault_id))

    def push(
        self, vault_id: str, content: str, title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PushResult:
        return self._run(self._ns.push(vault_id, content, title=title, metadata=metadata))

    def update_source_meta(self, vault_id: str, source_id: str,
                           set: dict | None = None,
                           remove: list[str] | None = None) -> dict:
        return self._run(self._ns.update_source_meta(
            vault_id, source_id, set=set, remove=remove))

    def list_meta_keys(self, vault_id: str) -> list[str]:
        return self._run(self._ns.list_meta_keys(vault_id))

    def declare_meta_key(self, vault_id: str, key: str) -> str:
        return self._run(self._ns.declare_meta_key(vault_id, key))

    def remove_meta_key(self, vault_id: str, key: str) -> bool:
        return self._run(self._ns.remove_meta_key(vault_id, key))

    def pull(
        self, vault_id: str, query: str | None = None, limit: int = 10,
        filters: dict | None = None,
    ) -> list[VaultItem]:
        return self._run(self._ns.pull(vault_id, query=query, limit=limit,
                                       filters=filters))


class Xysq:
    """Synchronous client for the xysq memory API.

    Usage::

        with Xysq(api_key="xysq_agent_...") as client:
            vault = client.vaults.create("Support Bot")
            client.vaults.push(vault.vault_id, "user: ...\\nagent: ...")
            hits = client.vaults.pull(vault.vault_id, "refund policy")

    Or without a context manager::

        client = Xysq(api_key="xysq_agent_...")
        hits = client.vaults.pull(vault_id, "user preferences")
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
        self.vaults = _SyncVaults(self._async_client.vaults, self._loop)
        self.threads = _SyncThreads(self._async_client.threads, self._loop)
        self.tags = _SyncTags(self._async_client.tags, self._loop)

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
