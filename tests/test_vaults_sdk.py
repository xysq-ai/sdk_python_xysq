"""Vaults namespace: create-in-project plumbing (3.5.1) + pii scrub (3.6.0)."""
from __future__ import annotations

import asyncio

import pytest

from xysq.exceptions import NotFoundError
from xysq.types import PushResult, Vault
from xysq.vaults import VaultsNamespace


class FakeHTTP:
    def __init__(self):
        self.sent = None

    async def post(self, path: str, json: dict | None = None):
        self.sent = (path, json)
        if path.endswith("/push"):
            return {"status": "captured", "id": "src1"}
        return {"vault_id": "v1", "name": json["name"], "kind": "agent",
                "project_id": json.get("project_id"),
                "pii_scrub": json.get("pii_scrub", False)}


def test_create_passes_project_id():
    async def run():
        http = FakeHTTP()
        ns = VaultsNamespace(http)
        v = await ns.create("support-kb", project_id="p1")
        assert isinstance(v, Vault)
        assert http.sent == ("/sdk/vaults",
                              {"name": "support-kb", "project_id": "p1", "pii_scrub": False})
        assert v.project_id == "p1"

        standalone = await ns.create("solo")
        assert standalone.project_id is None
    asyncio.run(run())


def test_sync_create_forwards_project_id():
    # the 3.5.1 sync wrapper accepted project_id and silently dropped it;
    # this pins the forwarding
    import inspect
    from xysq import _sync_client
    src = inspect.getsource(_sync_client)
    assert "self._ns.create(name, project_id=project_id, pii_scrub=pii_scrub)" in src


def test_create_passes_pii_scrub():
    async def run():
        http = FakeHTTP()
        ns = VaultsNamespace(http)
        v = await ns.create("cust", pii_scrub=True)
        assert http.sent == ("/sdk/vaults",
                              {"name": "cust", "project_id": None, "pii_scrub": True})
        assert v.pii_scrub is True

        default = await ns.create("plain")
        assert default.pii_scrub is False
    asyncio.run(run())


def test_push_includes_pii_flags_when_set():
    async def run():
        http = FakeHTTP()
        ns = VaultsNamespace(http)
        result = await ns.push("v1", "user: my ssn is ...", pii=True,
                                known_pii=["Alice Chen", "555-1234"])
        assert isinstance(result, PushResult)
        assert http.sent == ("/sdk/vaults/v1/push",
                              {"content": "user: my ssn is ...", "pii": True,
                               "known_pii": ["Alice Chen", "555-1234"]})
    asyncio.run(run())


def test_push_omits_pii_flags_when_none():
    async def run():
        http = FakeHTTP()
        ns = VaultsNamespace(http)
        await ns.push("v1", "user: hi")
        assert http.sent == ("/sdk/vaults/v1/push", {"content": "user: hi"})
    asyncio.run(run())


def test_sync_push_forwards_pii_flags():
    # match the 3.5.1 sync-forwarding pin pattern for the new push kwargs
    import inspect
    from xysq import _sync_client
    src = inspect.getsource(_sync_client)
    assert "pii=pii, known_pii=known_pii" in src


# -- one source: replace / delete (3.7.0) ------------------------------------


class _SourceHTTP:
    """Answers the two per-source routes, and can be told to 404 the delete."""

    def __init__(self, *, missing: bool = False):
        self.sent = None
        self._missing = missing

    async def post(self, path: str, json: dict | None = None):
        self.sent = (path, json)
        if path.endswith("/delete"):
            if self._missing:
                from xysq.exceptions import NotFoundError
                raise NotFoundError("not found", status_code=404)
            return {"id": "src1", "deleted": True, "retracted_fact_count": 2,
                    "pages_rewritten": 1, "pages_deleted": 0}
        return {"status": "pending", "id": "src1"}


def test_replace_source_keeps_the_id_and_reports_pending():
    async def run():
        http = _SourceHTTP()
        ns = VaultsNamespace(http)
        result = await ns.replace_source("v1", "src1", "we ship to the US only")
        assert isinstance(result, PushResult)
        assert result.id == "src1", "the caller's stable handle must survive"
        # pending, not captured: the wiki catches up on the next distill
        assert result.status == "pending"
        # an omitted hash sends NO key, rather than an explicit null the server
        # would have to tell apart from "the hash is literally None"
        assert http.sent == ("/sdk/vaults/v1/sources/src1/update",
                             {"content": "we ship to the US only"})
    asyncio.run(run())


def test_replace_source_forwards_every_optional_field():
    async def run():
        http = _SourceHTTP()
        ns = VaultsNamespace(http)
        await ns.replace_source("v1", "src1", "new text", title="Policy",
                                metadata={"source_kind": "stated"}, pii=True,
                                known_pii=["Alice Chen"],
                                expected_content_hash="abc123")
        assert http.sent[1] == {
            "content": "new text", "title": "Policy",
            "metadata": {"source_kind": "stated"}, "pii": True,
            "known_pii": ["Alice Chen"], "expected_content_hash": "abc123"}
    asyncio.run(run())


def test_delete_source_does_not_report_a_404_as_success():
    """CHANGED DELIBERATELY: this used to assert False on a 404.

    The iron wall answers 404 for four different things -- the source is not
    there, the vault is not there, you hold no role, your key has no grant
    covering this vault -- so "already gone" is one reading out of four. A
    cleanup loop over ids with a typo'd vault_id got False every time and
    concluded it had deleted everything. Let it raise; a caller retrying a
    delete it believes completed knows which case it is in and can catch."""
    async def run():
        ns = VaultsNamespace(_SourceHTTP())
        assert await ns.delete_source("v1", "src1") is True
        gone = VaultsNamespace(_SourceHTTP(missing=True))
        with pytest.raises(NotFoundError):
            await gone.delete_source("v1", "src1")
    asyncio.run(run())


def test_sync_forwards_the_source_kwargs():
    # same pin pattern as create/push above: the 3.5.1 sync wrapper silently
    # dropped a kwarg once, and nothing but a source check catches that
    import inspect
    from xysq import _sync_client
    src = inspect.getsource(_sync_client)
    assert "expected_content_hash=expected_content_hash" in src
    assert "self._ns.delete_source(vault_id, source_id)" in src
