"""Memory namespace — all memory operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xysq.exceptions import QuotaError, XysqError
from xysq.types import CaptureResult, MemoryItem, StatusResult, SynthesizeResult

if TYPE_CHECKING:
    from xysq._http import AsyncHTTPClient

_BASE = "/api/sdk"


class MemoryNamespace:
    """Async interface to xysq memory operations."""

    def __init__(self, http: AsyncHTTPClient, team_id: str | None = None) -> None:
        self._http = http
        self._team_id = team_id

    async def capture(
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
        """Store a memory. Returns processing status and tag feedback."""
        payload: dict[str, Any] = {"content": content}
        if context is not None:
            payload["context"] = context
        if tags is not None:
            payload["tags"] = tags
        if significance != "normal":
            payload["significance"] = significance
        if scope != "permanent":
            payload["scope"] = scope
        if memory_type is not None:
            payload["memory_type"] = memory_type
        if document_id is not None:
            payload["document_id"] = document_id
        if metadata is not None:
            payload["metadata"] = metadata
        if timestamp is not None:
            payload["timestamp"] = timestamp
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/memory/retain", json=payload)
        if data.get("status") == "limit_reached":
            raise QuotaError(data.get("message", "Memory quota reached."))
        if data.get("status") == "error":
            raise XysqError(data.get("message", "Unknown error"))
        return CaptureResult.model_validate(data)

    async def surface(
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
        """Retrieve memories relevant to a query."""
        payload: dict[str, Any] = {"query": query, "budget": budget}
        if types is not None:
            payload["types"] = types
        if intent is not None:
            payload["intent"] = intent
        if domain is not None:
            payload["domain"] = domain
        if scope is not None:
            payload["scope"] = scope
        if memory_type is not None:
            payload["memory_type"] = memory_type
        if agent_filter is not None:
            payload["agent_filter"] = agent_filter
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/memory/recall", json=payload)
        return [self._parse_memory(item) for item in data]

    async def synthesize(
        self,
        query: str,
        budget: str = "mid",
        response_schema: dict[str, Any] | None = None,
        write_back: bool = False,
    ) -> SynthesizeResult:
        """Synthesise an answer from memories."""
        payload: dict[str, Any] = {"query": query, "budget": budget}
        if response_schema is not None:
            payload["response_schema"] = response_schema
        if write_back:
            payload["write_back"] = write_back
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/memory/reflect", json=payload)
        if data.get("status") == "error":
            raise XysqError(data.get("message", "Unknown error"))
        return SynthesizeResult.model_validate(data)

    async def list(
        self,
        limit: int = 20,
        agent_filter: str | None = None,
    ) -> list[MemoryItem]:
        """List recent memories."""
        payload: dict[str, Any] = {"limit": limit}
        if agent_filter is not None:
            payload["agent_filter"] = agent_filter
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/memory/list", json=payload)
        return [self._parse_memory(item) for item in data]

    async def delete(self, memory_id: str) -> dict:
        """Delete a memory by ID."""
        payload: dict[str, Any] = {"memory_id": memory_id}
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/memory/delete", json=payload)
        return data

    async def status(self, memory_id: str) -> StatusResult:
        """Check the indexing status of a memory."""
        payload: dict[str, Any] = {"memory_id": memory_id}
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/memory/status", json=payload)
        return StatusResult.model_validate(data)

    async def tags(self) -> dict:
        """Fetch the valid tag taxonomy for memory capture."""
        payload: dict[str, Any] = {}
        self._inject_team(payload)
        return await self._http.post(f"{_BASE}/memory/tags", json=payload)

    async def wait(
        self,
        memory_id: str,
        timeout: float = 30.0,
        interval: float = 0.5,
    ) -> StatusResult:
        """Poll until memory reaches a terminal status (completed/failed) or timeout."""
        import asyncio

        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            result = await self.status(memory_id)
            if result.status in ("completed", "failed", "not_found"):
                return result
            if asyncio.get_event_loop().time() >= deadline:
                return result  # return last status on timeout
            await asyncio.sleep(interval)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _inject_team(self, payload: dict[str, Any]) -> None:
        if self._team_id is not None:
            payload["team_id"] = self._team_id

    @staticmethod
    def _parse_memory(item: dict[str, Any]) -> MemoryItem:
        """Map backend response to MemoryItem, handling _source -> source."""
        if "_source" in item:
            item = {**item, "source": item.pop("_source")}
        return MemoryItem.model_validate(item)
