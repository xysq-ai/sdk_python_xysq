"""Memory namespace — all memory operations."""

from typing import Any

from xysq._http import AsyncHTTPClient
from xysq.models import MemoryItem, ReflectResult

_BASE = "/api/agent"


class MemoryNamespace:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def retain(
        self,
        content: str,
        context: str | None = None,
        document_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> None:
        """Store a memory. Returns immediately; storage happens asynchronously."""
        payload: dict[str, Any] = {"content": content}
        if context is not None:
            payload["context"] = context
        if document_id is not None:
            payload["document_id"] = document_id
        if metadata is not None:
            payload["metadata"] = metadata
        if timestamp is not None:
            payload["timestamp"] = timestamp
        await self._http.post(f"{_BASE}/memory/retain", json=payload)

    async def recall(
        self,
        query: str,
        budget: str = "mid",
        types: list[str] | None = None,
        agent_filter: str | None = None,
    ) -> list[MemoryItem]:
        """Retrieve memories relevant to a query."""
        payload: dict[str, Any] = {"query": query, "budget": budget}
        if types is not None:
            payload["types"] = types
        if agent_filter is not None:
            payload["agent_filter"] = agent_filter
        data = await self._http.post(f"{_BASE}/memory/recall", json=payload)
        return [MemoryItem.model_validate(item) for item in data]

    async def reflect(
        self,
        query: str,
        budget: str = "mid",
        response_schema: dict[str, Any] | None = None,
    ) -> ReflectResult:
        """Synthesise an answer from memories."""
        payload: dict[str, Any] = {"query": query, "budget": budget}
        if response_schema is not None:
            payload["response_schema"] = response_schema
        data = await self._http.post(f"{_BASE}/memory/reflect", json=payload)
        # The provider may return {"answer": ..., ...} — normalise it
        return ReflectResult(
            answer=data.get("answer", str(data)),
            query=query,
        )

    async def list(
        self,
        limit: int = 20,
        agent_filter: str | None = None,
    ) -> list[MemoryItem]:
        """List recent memories."""
        params: dict[str, Any] = {"limit": limit}
        if agent_filter is not None:
            params["agent_filter"] = agent_filter
        data = await self._http.get(f"{_BASE}/memory/list", **params)
        return [MemoryItem.model_validate(item) for item in data]

    async def delete(self, memory_id: str) -> int:
        """Delete a memory. Returns the number of memory units deleted."""
        data = await self._http.delete(f"{_BASE}/memory/{memory_id}")
        return data.get("count", 0)
