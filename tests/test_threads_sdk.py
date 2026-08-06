"""Threads namespace + the XysqAgent persistence contract.

The agent test is the one that motivated the checkpointer spec: 30 turns,
kill the process (here: construct a fresh agent), point it at the SAME
(vault_id, thread_id), and the conversation is still there -- history is
server state, not a Python list that dies with the process.
"""
from __future__ import annotations

import asyncio
import sys
import types as _types

from xysq.threads import ThreadsNamespace
from xysq.types import ThreadWindow, Turn


class FakeHTTP:
    """Records requests; emulates the server's thread routes in memory."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.turns: dict[tuple[str, str], list[dict]] = {}
        self.floors: dict[tuple[str, str], int] = {}

    async def post(self, path: str, json: dict | None = None) -> dict:
        json = json or {}
        self.calls.append((path, json))
        vault_id = path.split("/")[3]
        key = (vault_id, json.get("thread_id", ""))
        turns = self.turns.setdefault(key, [])
        if path.endswith("/threads/append"):
            for t in turns:  # turn_key idempotency, like the real RPC
                if t.get("turn_key") == json["turn_key"]:
                    return {"status": "ok", "turn": t}
            seq = max([t["seq"] for t in turns], default=self.floors.get(key, 0)) + 1
            turn = {"seq": seq, "role": json["role"], "content": json["content"],
                    "created_at": "2026-08-06T00:00:00Z", "turn_key": json["turn_key"]}
            turns.append(turn)
            return {"status": "ok", "turn": turn}
        if path.endswith("/threads/read"):
            n = json.get("last_n") or 50
            window = turns[-n:]
            return {"status": "ok",
                    "turns": [{k: t[k] for k in ("seq", "role", "content", "created_at")}
                              for t in window],
                    "total_turns": len(turns),
                    "truncated": len(window) < len(turns),
                    "summary": None,
                    "flushed_through": 0}
        if path.endswith("/threads/list"):
            return {"status": "ok", "threads": [
                {"thread_id": t, "total_turns": len(v), "last_turn_at": None}
                for (_, t), v in self.turns.items() if _ == vault_id]}
        if path.endswith("/threads/flush"):
            return {"status": "ok", "flushed_turns": len(turns)}
        if path.endswith("/threads/clear"):
            self.floors[key] = max([t["seq"] for t in turns], default=0)
            self.turns[key] = []
            return {"status": "ok", "cleared_through": self.floors[key]}
        raise AssertionError(f"unexpected path {path}")


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_append_mints_a_turn_key_and_returns_seq():
    http = FakeHTTP()
    ns = ThreadsNamespace(http)
    turn = _run(ns.append("v1", "chat-1", "user", "hello"))
    assert isinstance(turn, Turn) and turn.seq == 1
    path, payload = http.calls[0]
    assert payload["turn_key"], "the SDK must mint an idempotency key"
    # a retry with the SAME key returns the same seq, no duplicate
    again = _run(ns.append("v1", "chat-1", "user", "hello",
                           turn_key=payload["turn_key"]))
    assert again.seq == 1
    assert len(http.turns[("v1", "chat-1")]) == 1


def test_read_window_shape_and_truncation():
    http = FakeHTTP()
    ns = ThreadsNamespace(http)
    for i in range(20):
        _run(ns.append("v1", "c", "user", f"t{i}"))
    w = _run(ns.read("v1", "c", last_n=5))
    assert isinstance(w, ThreadWindow)
    assert [t.seq for t in w.turns] == [16, 17, 18, 19, 20]
    assert w.truncated is True and w.total_turns == 20
    assert w.summary is None


def _fake_litellm(reply="ok!"):
    mod = _types.ModuleType("litellm")
    captured = {}

    def completion(model, api_key, messages):
        captured["messages"] = messages
        msg = _types.SimpleNamespace(content=reply)
        return _types.SimpleNamespace(choices=[_types.SimpleNamespace(message=msg)])

    mod.completion = completion
    mod._captured = captured
    return mod


class FakeSyncClient:
    """The sync Xysq surface XysqAgent touches, over one shared FakeHTTP."""

    def __init__(self, http: FakeHTTP):
        self._http = http
        ns = ThreadsNamespace(http)

        class _T:
            def append(s, *a, **k): return _run(ns.append(*a, **k))
            def read(s, *a, **k): return _run(ns.read(*a, **k))
            def clear(s, *a, **k): return _run(ns.clear(*a, **k))
        class _V:
            def pull(s, *a, **k): return []
            def push(s, *a, **k): return {"status": "captured"}
        self.threads, self.vaults = _T(), _V()


def test_agent_history_survives_a_fresh_instance(monkeypatch):
    """THE test: 30 turns, new process (new agent object), same thread ->
    the model sees the earlier conversation. The old agent kept history in
    a Python list; this exact test would have caught it."""
    monkeypatch.setitem(sys.modules, "litellm", _fake_litellm("noted."))
    from xysq.agent import XysqAgent

    http = FakeHTTP()
    a1 = XysqAgent(FakeSyncClient(http), "v1", "m", "k", thread_id="ticket-1",
                   recall=False, history_turns=100)
    for i in range(15):
        a1.chat(f"fact number {i}")
    assert len(http.turns[("v1", "ticket-1")]) == 30  # 15 user + 15 assistant

    # "restart": a brand-new agent, same thread
    a2 = XysqAgent(FakeSyncClient(http), "v1", "m", "k", thread_id="ticket-1",
                   recall=False, history_turns=100)
    a2.chat("do you remember fact number 0?")

    lite = sys.modules["litellm"]
    sent = lite._captured["messages"]
    assert any("fact number 0" in m["content"] for m in sent
               if m["role"] == "user"), "server-side history must reach the model"
    assert len([m for m in sent if m["role"] != "system"]) == 31


def test_agent_user_turn_is_durable_before_the_model_runs(monkeypatch):
    """A crash mid-turn loses the reply, never the question."""
    mod = _fake_litellm()

    def boom(**_):
        raise RuntimeError("provider down")
    mod.completion = boom
    monkeypatch.setitem(sys.modules, "litellm", mod)
    from xysq.agent import XysqAgent

    http = FakeHTTP()
    agent = XysqAgent(FakeSyncClient(http), "v1", "m", "k", thread_id="t",
                      recall=False)
    try:
        agent.chat("the question that must survive")
    except RuntimeError:
        pass
    turns = http.turns[("v1", "t")]
    assert len(turns) == 1 and turns[0]["content"] == "the question that must survive"


def test_clear_never_reuses_seq(monkeypatch):
    monkeypatch.setitem(sys.modules, "litellm", _fake_litellm())
    from xysq.agent import XysqAgent

    http = FakeHTTP()
    agent = XysqAgent(FakeSyncClient(http), "v1", "m", "k", thread_id="t",
                      recall=False)
    agent.chat("one")
    agent.clear_history()
    agent.chat("two")
    turns = http.turns[("v1", "t")]
    assert turns[0]["seq"] == 3, "seq keeps counting after clear -- no reuse"
