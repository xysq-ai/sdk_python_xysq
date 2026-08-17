"""Vaults namespace: create-in-project plumbing (3.5.1)."""
from __future__ import annotations

import asyncio

from xysq.types import Vault
from xysq.vaults import VaultsNamespace


class FakeHTTP:
    def __init__(self):
        self.sent = None

    async def post(self, path: str, json: dict | None = None):
        self.sent = (path, json)
        return {"vault_id": "v1", "name": json["name"], "kind": "agent",
                "project_id": json.get("project_id")}


def test_create_passes_project_id():
    async def run():
        http = FakeHTTP()
        ns = VaultsNamespace(http)
        v = await ns.create("support-kb", project_id="p1")
        assert isinstance(v, Vault)
        assert http.sent == ("/sdk/vaults", {"name": "support-kb", "project_id": "p1"})
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
    assert "self._ns.create(name, project_id=project_id)" in src
