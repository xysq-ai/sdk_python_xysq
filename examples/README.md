# xysq SDK — Examples

All examples read credentials from a `.env` file in this directory (or the project root):

```
XYSQ_API_KEY=xysq_...
XYSQ_TEAM_ID=...         # required for 03_team_memory.py
OPENAI_API_KEY=sk-...    # required for 02, 05, 06 (or any other LiteLLM provider key)
```

Install dependencies:

```bash
pip install 'xysq[agent] @ git+https://github.com/xysq-ai/sdk_python_xysq.git'
```

---

## 01 — Basic Memory

**[01_basic_memory.py](01_basic_memory.py)**

The "hello world" of xysq. Covers the four core operations in sequence:

1. **Capture** three memories with tags and significance levels
2. **Surface** relevant memories with a natural language query
3. **Synthesize** a structured answer from everything in the vault
4. **List** all stored memories with their metadata

No LLM required — this example runs against the xysq API only.

```bash
python 01_basic_memory.py
```

---

## 02 — Multi-Turn Chatbot with Memory

**[02_chatbot_with_memory.py](02_chatbot_with_memory.py)**

An interactive terminal chatbot that remembers across turns. On every message it surfaces relevant memories, injects them into the system prompt as a `<memory>` block, calls the LLM via LiteLLM, and captures the exchange back to xysq.

Start a conversation, close it, reopen — the bot picks up where you left off.

```bash
python 02_chatbot_with_memory.py
# Type messages, press Enter. Type 'quit' to exit.
```

Requires: `OPENAI_API_KEY` (or set `LITELLM_MODEL` + the matching provider key)

---

## 03 — Team Memory

**[03_team_memory.py](03_team_memory.py)**

Shows two "agents" sharing a single team vault. Agent 1 captures three team decisions (architecture, process, API standards). Agent 2 — using the same `client.team(team_id)` scope — surfaces and synthesizes from those decisions without any direct handoff.

Demonstrates that team vaults are the shared context layer: one agent writes, any other reads.

```bash
python 03_team_memory.py
```

Requires: `XYSQ_TEAM_ID`

---

## 04 — Knowledge Base

**[04_knowledge_base.py](04_knowledge_base.py)**

Indexes three types of knowledge sources into the vault:

- A **link** (fetched and indexed by xysq)
- A **code snippet** (retry utility function)
- A **quote** (an Architecture Decision Record)

Then waits for indexing, lists all sources, and shows how the indexed knowledge surfaces automatically through `memory.surface()` and `memory.synthesize()` — no separate knowledge query needed.

```bash
python 04_knowledge_base.py
```

---

## 05 — Agent with Tool Calling

**[05_agent_with_tools.py](05_agent_with_tools.py)**

A full LiteLLM tool-calling loop where the LLM decides when to invoke xysq tools. The agent is given `XysqLiteLLMTools` and runs two turns:

- **Turn 1:** user states a coding preference — the model calls `xysq_capture` to store it
- **Turn 2:** user asks a question — the model calls `xysq_surface` or `xysq_synthesize` to recall it before answering

Shows the tool-calling roundtrip: definitions → model call → execute → feed results back → final response.

```bash
python 05_agent_with_tools.py
```

Requires: `OPENAI_API_KEY` (or any LiteLLM-compatible provider)

---

## 06 — XysqAgent with Context Strategies

**[06_xysq_agent.py](06_xysq_agent.py)**

Demonstrates `XysqAgent` with three different context strategies across three sessions:

- **Session 1 — Surface strategy:** raw memory items injected into the system prompt on each turn
- **Session 2 — Synthesize strategy:** a fresh agent instance that recalls via synthesis, proving memory persists across instances
- **Session 3 — Custom AdaptiveStrategy:** synthesizes on the first turn for a broad overview, then switches to surface on follow-ups for precise recall

A good reference for building your own `ContextStrategy` implementation.

```bash
python 06_xysq_agent.py
```

Requires: `OPENAI_API_KEY` (or set `LITELLM_MODEL` + matching provider key)
