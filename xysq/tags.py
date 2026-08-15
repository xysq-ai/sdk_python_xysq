"""Tags namespace -- a controlled vocabulary for organizing sources.

One vocabulary per USER, spanning all your vaults: define tags once
(``client.tags.create``), then attach them to any captured source. The server
seeds a small starter set on first use; unknown names on apply are echoed
back, never auto-created (the vocabulary stays curated).

    async with AsyncXysq(api_key="xysq_agent_...") as client:
        tags = await client.tags.list()
        await client.tags.create("deploy")
        await client.tags.apply(vault_id, source_id, add=["deploy"])

Names are slugs: 1-30 chars of ``a-z``, ``0-9``, ``-`` (starting alnum);
the server lowercases and trims for you. Scoped recall by tag (pull
``filters``) lands with the server's scoped-retrieval wave.
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
