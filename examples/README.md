# xysq SDK — Examples

Install dependencies:

```bash
pip install 'xysq[agent] @ git+https://github.com/xysq-ai/sdk_python_xysq.git'
```

Create a `.env` file in this directory (or the project root) and fill in the relevant keys for the examples you want to run:

```
# xysq — required for all examples
XYSQ_API_KEY=xysq_...

# xysq — required for team examples (03)
XYSQ_TEAM_ID=...

# LLM provider — required for 02, 05, 06
# Set the key for whichever provider you use (see section below)
OPENAI_API_KEY=sk-...
```

---

## Using different LLM providers

Examples 02, 05, and 06 use [LiteLLM](https://github.com/BerriAI/litellm), which supports any major provider through a unified interface. You choose your provider by setting two things:

1. **`LITELLM_MODEL`** — the model string to use (read by the example scripts)
2. **The matching API key env var** — picked up automatically by LiteLLM

LiteLLM identifies the provider from the **`provider/model-name` prefix** in the model string. No other configuration is needed.

### Provider reference

| Provider | API key env var | Example `LITELLM_MODEL` value |
|---|---|---|
| **OpenAI** | `OPENAI_API_KEY` | `openai/gpt-4o` |
| **Anthropic** | `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4-20250514` |
| **Google Gemini** | `GEMINI_API_KEY` | `gemini/gemini-2.0-flash` |
| **Groq** | `GROQ_API_KEY` | `groq/llama3-8b-8192` |
| **Mistral** | `MISTRAL_API_KEY` | `mistral/mistral-small-latest` |
| **Cohere** | `COHERE_API_KEY` | `cohere_chat/command-a-03-2025` |
| **Azure OpenAI** | `AZURE_API_KEY` + `AZURE_API_BASE` + `AZURE_API_VERSION` | `azure/your-deployment-name` |

### OpenAI (default)

```
OPENAI_API_KEY=sk-...
LITELLM_MODEL=openai/gpt-4o
```

### Anthropic

```
ANTHROPIC_API_KEY=sk-ant-...
LITELLM_MODEL=anthropic/claude-sonnet-4-20250514
```

### Google Gemini

Get a key at [aistudio.google.com](https://aistudio.google.com/app/apikey).

```
GEMINI_API_KEY=...
LITELLM_MODEL=gemini/gemini-2.0-flash
```

### Groq

```
GROQ_API_KEY=gsk_...
LITELLM_MODEL=groq/llama3-8b-8192
```

### Mistral

```
MISTRAL_API_KEY=...
LITELLM_MODEL=mistral/mistral-small-latest
```

### Azure OpenAI

Azure requires three extra variables in addition to the model string:

```
AZURE_API_KEY=...
AZURE_API_BASE=https://your-resource.openai.azure.com
AZURE_API_VERSION=2024-02-01
LITELLM_MODEL=azure/your-deployment-name
```

---

If `LITELLM_MODEL` is not set, the example scripts default to `gpt-4o-mini` (OpenAI). Just set `OPENAI_API_KEY` and run.

---

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

Requires: an LLM provider key (see [provider reference](#provider-reference) above)

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

Requires: an LLM provider key (see [provider reference](#provider-reference) above)

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

Requires: an LLM provider key (see [provider reference](#provider-reference) above)
