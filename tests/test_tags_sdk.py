"""Tags namespace: vocabulary CRUD + apply against a route-faithful fake."""
from __future__ import annotations

import asyncio
import uuid

from xysq.tags import TagsNamespace
from xysq.types import SourceTagsResult, Tag

SEED = ("work", "health", "personal", "finance", "tech", "pii", "confidential")


class FakeHTTP:
    """Emulates the /sdk tag routes: per-user vocabulary, seeded on first
    read, unknown apply names echoed back (never created)."""

    def __init__(self):
        self.tags: dict[str, str] = {}       # tag_id -> name
        self.links: dict[str, set[str]] = {} # source_id -> tag_ids
        self.seeded = False

    def _seed(self):
        if not self.seeded:
            for n in SEED:
                self.tags[uuid.uuid4().hex] = n
            self.seeded = True

    async def get(self, path: str):
        assert path == "/sdk/tags"
        self._seed()
        return {"tags": [
            {"tag_id": t, "name": n, "created_by": "system",
             "applied": sum(1 for s in self.links.values() if t in s)}
            for t, n in self.tags.items()]}

    async def post(self, path: str, json: dict | None = None):
        json = json or {}
        if path == "/sdk/tags":
            self._seed()
            tid = uuid.uuid4().hex
            self.tags[tid] = json["name"].strip().lower()
            return {"tag_id": tid, "name": self.tags[tid]}
        if path.endswith("/update") and "/sources/" not in path:
            tid = path.split("/")[-2]
            self.tags[tid] = json["name"]
            return {"tag_id": tid, "name": json["name"]}
        if path.endswith("/delete"):
            tid = path.split("/")[-2]
            n = sum(1 for s in self.links.values() if tid in s)
            self.tags.pop(tid)
            for s in self.links.values():
                s.discard(tid)
            return {"deleted": True, "was_applied_to": n}
        # apply: /sdk/vaults/{v}/sources/{s}/tags/update
        source_id = path.split("/")[-3]
        by_name = {n: t for t, n in self.tags.items()}
        cur = self.links.setdefault(source_id, set())
        applied, removed, unknown = [], [], []
        for n in json.get("add", []):
            if n in by_name:
                cur.add(by_name[n]); applied.append(n)
            else:
                unknown.append(n)
        for n in json.get("remove", []):
            if n in by_name and by_name[n] in cur:
                cur.discard(by_name[n]); removed.append(n)
            elif n not in by_name:
                unknown.append(n)
        return {"applied": applied, "removed": removed, "unknown": unknown,
                "tags": sorted(self.tags[t] for t in cur)}


def test_tags_roundtrip():
    async def run():
        ns = TagsNamespace(FakeHTTP())
        tags = await ns.list()
        assert isinstance(tags[0], Tag)
        assert {t.name for t in tags} == set(SEED)

        created = await ns.create("Deploy")
        assert created.name == "deploy"  # server normalizes

        renamed = await ns.rename(created.tag_id, "deploys")
        assert renamed.name == "deploys"

        out = await ns.apply("v1", "src1", add=["deploys", "nope"])
        assert isinstance(out, SourceTagsResult)
        assert out.applied == ["deploys"]
        assert out.unknown == ["nope"]
        assert out.tags == ["deploys"]

        assert await ns.delete(created.tag_id) == 1
    asyncio.run(run())


def test_sync_client_exposes_tags():
    from xysq._sync_client import Xysq
    c = Xysq(api_key="xysq_test")
    try:
        assert hasattr(c.tags, "apply") and hasattr(c.tags, "list")
    finally:
        c.close()
