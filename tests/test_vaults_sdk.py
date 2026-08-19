"""Vaults namespace: create-in-project plumbing (3.5.1) + pii scrub (3.6.0)."""
from __future__ import annotations

import asyncio

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
