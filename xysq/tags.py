"""Tags namespace -- PROJECT-level vocabularies for your agents.

The SDK manages agent resources: each project carries one shared tag
vocabulary its agents apply. Personal and team tags live in the app UI;
agent-global lives at /agents/tags. Deleting archives (sources stay
tagged; ``restore`` revives); archived tags list last with
``archived=True``.

    async with AsyncXysq(api_key="xysq_agent_...") as client:
        await client.tags.create(project_id, "deploy")
        tags = await client.tags.list(project_id)
        await client.tags.apply(vault_id, source_id, add=["deploy"])
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xysq.types import SourceTagsResult, Tag

if TYPE_CHECKING:
    from xysq._http import AsyncHTTPClient


class TagsNamespace:
    """Async interface to the /sdk tag operations."""

    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def list(self, project_id: str) -> list[Tag]:
        """The PROJECT's vocabulary with live applied-counts. The SDK manages
        agent resources only: personal and team tags live in the app UI."""
        data = await self._http.get(f"/sdk/projects/{project_id}/tags")
        return [Tag.model_validate(t) for t in data.get("tags", [])]

    async def create(self, project_id: str, name: str) -> Tag:
        """Create a project tag. 409 if the name exists (or exists archived)."""
        data = await self._http.post(f"/sdk/projects/{project_id}/tags",
                                     json={"name": name})
        return Tag.model_validate({**data, "created_by": "user", "applied": 0})

    async def rename(self, project_id: str, tag_id: str, name: str) -> Tag:
        """Rename a project tag; every application follows instantly."""
        data = await self._http.post(
            f"/sdk/projects/{project_id}/tags/{tag_id}/update", json={"name": name})
        return Tag.model_validate({**data, "created_by": "user", "applied": 0})

    async def delete(self, project_id: str, tag_id: str) -> int:
        """ARCHIVE a project tag: sources stay tagged, the tag leaves the
        pickers, restore() brings it back. Returns the applied count."""
        data = await self._http.post(
            f"/sdk/projects/{project_id}/tags/{tag_id}/delete", json={})
        return int(data.get("was_applied_to", 0))

    async def restore(self, project_id: str, tag_id: str) -> bool:
        """Un-archive a project tag."""
        data = await self._http.post(
            f"/sdk/projects/{project_id}/tags/{tag_id}/restore", json={})
        return bool(data.get("restored"))

    async def apply(
        self, vault_id: str, source_id: str,
        add: list[str] | None = None, remove: list[str] | None = None,
    ) -> SourceTagsResult:
        """Attach/detach tags on a captured source (by name), resolving
        against the VAULT's context: its project's vocabulary, then your
        agent-global registry. Unknown names come back in ``unknown`` --
        nothing is auto-created and the call never fails over one."""
        data = await self._http.post(
            f"/sdk/vaults/{vault_id}/sources/{source_id}/tags/update",
            json={"add": add or [], "remove": remove or []})
        return SourceTagsResult.model_validate(data)
