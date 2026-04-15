"""Knowledge namespace — knowledge source operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xysq.exceptions import XysqError
from xysq.types import KnowledgeSource, StatusResult

if TYPE_CHECKING:
    from xysq._http import AsyncHTTPClient

_BASE = "/api/sdk"


class KnowledgeNamespace:
    """Async interface to xysq knowledge operations."""

    def __init__(self, http: AsyncHTTPClient, team_id: str | None = None) -> None:
        self._http = http
        self._team_id = team_id

    async def add(
        self,
        type: str,
        content: str | None = None,
        url: str | None = None,
        title: str | None = None,
        location: str | None = None,
        session_context: str | None = None,
        confidence: str = "medium",
    ) -> KnowledgeSource:
        """Add a knowledge source."""
        payload: dict[str, Any] = {"type": type}
        if content is not None:
            payload["content"] = content
        if url is not None:
            payload["url"] = url
        if title is not None:
            payload["title"] = title
        if location is not None:
            payload["location"] = location
        if session_context is not None:
            payload["session_context"] = session_context
        if confidence != "medium":
            payload["confidence"] = confidence
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/knowledge/add", json=payload)
        if data.get("status") == "error":
            raise XysqError(data.get("message", "Unknown error"))
        return KnowledgeSource(
            source_id=data.get("source_id", ""),
            type=type,
            title=title,
            status=data.get("status", "pending"),
            url=url,
            location=location,
        )

    async def list(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        type: str | None = None,
    ) -> list[KnowledgeSource]:
        """List knowledge sources."""
        payload: dict[str, Any] = {"limit": limit, "offset": offset}
        if status is not None:
            payload["status"] = status
        if type is not None:
            payload["type"] = type
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/knowledge/list", json=payload)
        sources = data.get("sources", []) if isinstance(data, dict) else data
        return [
            KnowledgeSource(
                source_id=item.get("source_id", ""),
                type=item.get("type", ""),
                title=item.get("title"),
                status=item.get("status", "pending"),
                url=item.get("url"),
                location=item.get("location"),
                created_at=item.get("added_at", item.get("created_at", "")),
            )
            for item in sources
        ]

    async def status(self, source_id: str) -> StatusResult:
        """Check the indexing status of a knowledge source."""
        payload: dict[str, Any] = {"source_id": source_id}
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/knowledge/status", json=payload)
        return StatusResult.model_validate(data)

    async def wait(
        self,
        source_id: str,
        timeout: float = 30.0,
        interval: float = 0.5,
    ) -> StatusResult:
        """Poll until source reaches a terminal status (indexed/failed) or timeout."""
        import asyncio

        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            result = await self.status(source_id)
            if result.status in ("indexed", "failed", "not_found"):
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
