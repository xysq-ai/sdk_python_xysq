"""Threads namespace -- the checkpointer: a live conversation's turns.

Ordered, verbatim, read-your-writes -- the working memory an agent rebuilds
its context from mid-conversation. Long-term memory needs nothing extra: the
server promotes turns automatically (and on ``flush()``/``clear()``), distills
them, and they become pull()-able like any other content.

    async with AsyncXysq(api_key="xysq_agent_...") as client:
        t = await client.threads.append(vault_id, "chat-1", "user", "hi")
        window = await client.threads.read(vault_id, "chat-1", last_n=12)

``thread_id`` is yours: any stable id up to 200 chars of [A-Za-z0-9._:-],
usually your own conversation id.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import asyncio

from xysq.exceptions import XysqError
from xysq.types import ThreadInfo, ThreadWindow, Turn

if TYPE_CHECKING:
    from xysq._http import AsyncHTTPClient

_BASE = "/sdk/vaults"


class ThreadsNamespace:
    """Async interface to the /sdk thread operations."""

    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def append(
        self, vault_id: str, thread_id: str, role: str, content: str,
        turn_key: str | None = None,
    ) -> Turn:
        """Append one turn; its allocated ``seq`` comes back. Safe under
        TRANSPORT retries: a ``turn_key`` is minted here (once per logical
        turn, before the transport's own retry loop), so a committed insert
        with a lost response returns the SAME turn instead of duplicating it.
        If YOUR code retries a failed append call, pass the same ``turn_key``
        on the retry -- a fresh call mints a fresh key and is a new turn.

        A 409 (seq contention on a hot thread) is retried here with the same
        key: idempotency makes that retry safe, and the transport deliberately
        does not retry 409s in general."""
        payload: dict[str, Any] = {
            "thread_id": thread_id, "role": role, "content": content,
            "turn_key": turn_key or uuid.uuid4().hex,
        }
        last: XysqError | None = None
        for attempt in range(3):
            try:
                data = await self._http.post(
                    f"{_BASE}/{vault_id}/threads/append", json=payload)
                break
            except XysqError as exc:
                if getattr(exc, "status_code", None) != 409:
                    raise
                last = exc
                await asyncio.sleep(0.2 * (attempt + 1))
        else:
            raise last  # type: ignore[misc]
        turn = data.get("turn")
        if not turn:
            # never fabricate a Turn(seq=0): the returned seq is the caller's
            # write-verification handle (spec 5), a fake zero breaks it
            raise XysqError("append response carried no turn")
        return Turn.model_validate(turn)

    async def read(
        self, vault_id: str, thread_id: str,
        last_n: int | None = None, token_budget: int | None = None,
    ) -> ThreadWindow:
        """The newest turns, oldest-first. Bounded always (server default 50,
        max 500); when both bounds are given the tighter wins. Check
        ``truncated`` -- a cut window is flagged, never silent."""
        payload: dict[str, Any] = {"thread_id": thread_id}
        if last_n is not None:
            payload["last_n"] = last_n
        if token_budget is not None:
            payload["token_budget"] = token_budget
        data = await self._http.post(f"{_BASE}/{vault_id}/threads/read", json=payload)
        return ThreadWindow.model_validate(data)

    async def list(self, vault_id: str) -> list[ThreadInfo]:
        """The vault's threads, newest first -- restart recovery."""
        data = await self._http.post(f"{_BASE}/{vault_id}/threads/list", json={})
        return [ThreadInfo.model_validate(t) for t in data.get("threads", [])]

    async def flush(self, vault_id: str, thread_id: str) -> int:
        """Promote unflushed turns to long-term memory NOW (the server also
        auto-flushes periodically and sweeps idle threads). Returns how many
        turns were promoted."""
        data = await self._http.post(
            f"{_BASE}/{vault_id}/threads/flush", json={"thread_id": thread_id})
        return int(data.get("flushed_turns", 0))

    async def clear(self, vault_id: str, thread_id: str) -> int:
        """Flush, then wipe the working memory. Never discards: unflushed
        turns are promoted first. The distilled long-term memory stays.
        Sequence numbers are never reused after a clear."""
        data = await self._http.post(
            f"{_BASE}/{vault_id}/threads/clear", json={"thread_id": thread_id})
        return int(data.get("cleared_through", 0))
