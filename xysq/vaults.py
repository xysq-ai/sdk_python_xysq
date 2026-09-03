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

    async def create(self, name: str, project_id: str | None = None,
                      pii_scrub: bool = False) -> Vault:
        """Create a new agent vault. Requires an agent-class API key.
        Pass ``project_id`` to create it inside a project -- the vault then
        resolves the project's tag vocabulary on apply and filters.

        ``pii_scrub`` makes this vault's default: every push launders content
        (strips emails, phone numbers, and anything in a push's ``known_pii``)
        before it's stored, and a push that can't be scrubbed clean gets a
        422 with nothing stored. Override per push with ``push(..., pii=...)``."""
        data = await self._http.post(
            _BASE, json={"name": name, "project_id": project_id,
                         "pii_scrub": pii_scrub})
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
        pii: bool | None = None,
        known_pii: list[str] | None = None,
    ) -> PushResult:
        """Push VERBATIM content into a vault. The server distills it into the
        vault's wiki in the background, so this returns immediately.

        Pass the conversation as it happened, turn by turn, e.g.::

            "user: <what they said>\\nagent: <what you replied>"

        Do NOT summarize -- the server extracts the details. Group multiple
        pushes from one conversation with a stable ``metadata={"session_id": ...}``
        so they append to one source instead of fragmenting.

        ``pii`` overrides the vault's ``pii_scrub`` setting for just this push
        (``None`` inherits it). When scrubbing is on, content is laundered
        before storage; a 422 means it could not be scrubbed clean and nothing
        was stored. ``known_pii`` is a list of names/identifiers to redact even
        if they don't match a built-in pattern -- used transiently for this
        scrub only, never stored."""
        payload: dict[str, Any] = {"content": content}
        if title is not None:
            payload["title"] = title
        if metadata is not None:
            payload["metadata"] = metadata
        if pii is not None:
            payload["pii"] = pii
        if known_pii is not None:
            payload["known_pii"] = known_pii
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

    # -- one source: replace its bytes, or remove it -------------------------

    async def replace_source(
        self,
        vault_id: str,
        source_id: str,
        content: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        pii: bool | None = None,
        known_pii: list[str] | None = None,
        expected_content_hash: str | None = None,
    ) -> PushResult:
        """Rewrite a source's content UNDER THE SAME ``source_id`` (the ``id``
        from ``push``). Use this instead of delete-then-push when you own a
        source that changes -- a questionnaire answer, a policy page, a profile
        -- because a push mints a NEW id and your stable handle would change on
        every save.

        ACCEPTED, NOT APPLIED. The new content is stored when this returns, and
        the vault's wiki catches up on the next distill of that vault. For that
        window a pull can still cite the statement you just replaced. The
        returned ``status`` is ``"pending"``, not ``"captured"``, and says so.

        ``metadata`` MERGES into what the source already carries, so keys you
        don't mention (``source_kind``, say) survive the replace. Use
        ``update_source_meta(remove=[...])`` to take one away.

        ``expected_content_hash`` is optional. Pass the hash you last saw and a
        409 tells you somebody else wrote in between; omit it and you overwrite
        whatever is there. Prior versions are kept server-side either way, so a
        lost race loses only the newest text.

        ``pii`` and ``known_pii`` behave exactly as they do on ``push``."""
        payload: dict[str, Any] = {"content": content}
        if title is not None:
            payload["title"] = title
        if metadata is not None:
            payload["metadata"] = metadata
        if pii is not None:
            payload["pii"] = pii
        if known_pii is not None:
            payload["known_pii"] = known_pii
        if expected_content_hash is not None:
            payload["expected_content_hash"] = expected_content_hash
        data = await self._http.post(
            f"{_BASE}/{vault_id}/sources/{source_id}/update", json=payload)
        return PushResult.model_validate(data)

    async def delete_source(self, vault_id: str, source_id: str) -> bool:
        """Delete ONE source. IRREVERSIBLE. Returns True if it was there,
        False if it was already gone (a 404), so a blind retry needs no
        special case.

        Four things this actually does, plainly:

        1. It removes the source, its search chunks, and every fact the source
           grounded, along with the lines those facts held up.
        2. It ALSO retracts facts that were cited to another source as well.
           A fact is only as grounded as its weakest citation, so the whole
           fact goes. Those are re-derivable -- the surviving source is still
           in the vault -- but nothing re-derives them for you, because
           nothing re-distills a source that did not change.
        3. It does NOT erase every copy of the words. Page history in the
           vault's git repo and the distill run log keep them. If you need
           real erasure, this is not it.
        4. Deleting a vault's LAST source does not delete the vault. Use
           ``delete(vault_id)`` for that.

        Needs a key with ``read_write`` or ``admin`` on this vault: a
        write-only ingest key can push and cannot erase."""
        from xysq.exceptions import NotFoundError
        try:
            await self._http.post(
                f"{_BASE}/{vault_id}/sources/{source_id}/delete", json={})
        except NotFoundError:
            # already gone (or never here). The engine-level work is
            # idempotent, so a retry after a crashed delete is safe; a
            # COMPLETED delete answers 404, and that is success from here
            return False
        return True

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
