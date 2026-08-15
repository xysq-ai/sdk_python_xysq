"""Vaults namespace -- the /sdk vault API.

An agent owns multiple vaults, each an independent memory (its own wiki + facts).
The API key (an AGENT-class key) authorizes all of them; the vault is named in
the path. Push verbatim content, pull ranked context, and manage vaults.

    async with AsyncXysq(api_key="xysq_agent_...") as client:
        v = await client.vaults.create("Work Notes")
        await client.vaults.push(v.vault_id, "user: ...\\nagent: ...")
        hits = await client.vaults.pull(v.vault_id, "what did we decide")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xysq.types import PushResult, Vault, VaultItem

if TYPE_CHECKING:
    from xysq._http import AsyncHTTPClient

_BASE = "/sdk/vaults"


class VaultsNamespace:
    """Async interface to the /sdk vault operations."""

    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    # -- vault CRUD ----------------------------------------------------------

    async def create(self, name: str) -> Vault:
        """Create a new agent vault. Requires an agent-class API key."""
        data = await self._http.post(_BASE, json={"name": name})
        return Vault.model_validate(data)

    async def list(self) -> list[Vault]:
        """List the vaults this key may see (an agent key -> agent vaults)."""
        data = await self._http.get(_BASE)
        return [Vault.model_validate(v) for v in data.get("items", [])]

    async def rename(self, vault_id: str, name: str) -> None:
        """Rename a vault."""
        await self._http.post(f"{_BASE}/{vault_id}/update", json={"name": name})

    async def delete(self, vault_id: str) -> None:
        """Delete a vault -- permanently erases its memory (pages, sources,
        vectors, git repo). The personal vault cannot be deleted here."""
        await self._http.post(f"{_BASE}/{vault_id}/delete", json={})

    # -- memory --------------------------------------------------------------

    async def push(
        self,
        vault_id: str,
        content: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PushResult:
        """Push VERBATIM content into a vault. The server distills it into the
        vault's wiki in the background, so this returns immediately.

        Pass the conversation as it happened, turn by turn, e.g.::

            "user: <what they said>\\nagent: <what you replied>"

        Do NOT summarize -- the server extracts the details. Group multiple
        pushes from one conversation with a stable ``metadata={"session_id": ...}``
        so they append to one source instead of fragmenting."""
        payload: dict[str, Any] = {"content": content}
        if title is not None:
            payload["title"] = title
        if metadata is not None:
            payload["metadata"] = metadata
        data = await self._http.post(f"{_BASE}/{vault_id}/push", json=payload)
        return PushResult.model_validate(data)

    async def pull(
        self, vault_id: str, query: str | None = None, limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VaultItem]:
        """Pull ranked context from a vault. Omit ``query`` for the most recent
        context. Returns the assembled items (the server owns retrieval).

        ``filters`` narrows the search, two composable kinds:
        ``{"tags": ["deploy"]}`` searches ONLY sources you tagged (hard
        inclusion; unknown names are a 400 listing your vocabulary), and
        ``{"meta": {key: value}}`` filters by a DECLARED key with
        match-or-absent semantics: keeps everything matching AND everything
        without the key; only contradicting sources drop."""
        payload: dict[str, Any] = {"limit": limit}
        if query is not None:
            payload["query"] = query
        if filters is not None:
            payload["filters"] = filters
        data = await self._http.post(f"{_BASE}/{vault_id}/pull", json=payload)
        return [VaultItem.model_validate(it) for it in data.get("items", [])]

    # -- filterable metadata (declared keys; match-or-absent filters) ---------

    async def list_meta_keys(self, vault_id: str) -> list[str]:
        """The vault's declared filterable keys -- read before filtering."""
        data = await self._http.get(f"{_BASE}/{vault_id}/meta-keys")
        return [k["key"] for k in data.get("keys", [])]

    async def declare_meta_key(self, vault_id: str, key: str) -> str:
        """Declare a key as filterable. The server indexes existing sources in
        the background and every future push at capture."""
        data = await self._http.post(
            f"{_BASE}/{vault_id}/meta-keys", json={"key": key})
        return data["key"]

    async def remove_meta_key(self, vault_id: str, key: str) -> bool:
        """Undeclare: stops indexing and drops the key's index. The metadata
        on your sources is untouched."""
        data = await self._http.post(
            f"{_BASE}/{vault_id}/meta-keys/{key}/delete", json={})
        return bool(data.get("removed"))

    async def update_source_meta(
        self, vault_id: str, source_id: str,
        set: dict[str, Any] | None = None, remove: list[str] | None = None,
    ) -> dict[str, Any]:
        """Set/remove DECLARED metadata keys on an EXISTING source -- the
        after-the-fact twin of ``tags.apply``. Unknown (undeclared) keys are
        echoed back in ``unknown``, never written; the filter index updates
        immediately. Returns {applied, removed, unknown}."""
        return await self._http.post(
            f"{_BASE}/{vault_id}/sources/{source_id}/meta/update",
            json={"set": set or {}, "remove": remove or []})
