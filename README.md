# xysq Python SDK

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-xysq.ai-00b89a)](https://docs.xysq.ai/sdk/getting-started)

The official Python SDK for [xysq](https://xysq.ai) — a consent-first memory layer for AI agents. Give your agents persistent memory across sessions, share context across teams, and build agents that remember.

---

## Installation

```bash
pip install git+https://github.com/xysq-ai/sdk_python_xysq.git
```

Install optional extras for LiteLLM or Anthropic integrations:

```bash
pip install 'xysq[agent] @ git+https://github.com/xysq-ai/sdk_python_xysq.git'
pip install 'xysq[claude] @ git+https://github.com/xysq-ai/sdk_python_xysq.git'
pip install 'xysq[all] @ git+https://github.com/xysq-ai/sdk_python_xysq.git'
```

**Requires Python 3.11+**

---

## Quickstart

Get an API key at [app.xysq.ai/connect](https://app.xysq.ai/connect). Add it to a `.env` file:

```
XYSQ_API_KEY=xysq_...
```

```python
from dotenv import load_dotenv
from xysq import Xysq

load_dotenv()

with Xysq() as client:
    # Capture a memory
    client.memory.capture(
        content="User prefers type hints in all Python code",
        tags=["coding-style", "python"],
    )

    # Surface relevant memories
    memories = client.memory.surface("Python coding preferences")
    for m in memories:
        print(m.text)

    # Synthesize an answer from memory
    result = client.memory.synthesize("What are the user's coding preferences?")
    print(result.answer)
```

---

## Table of Contents

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Core Concepts](#core-concepts)
- [API Reference](#api-reference)
  - [Memory](#memory)
  - [Knowledge Base](#knowledge-base)
  - [Team Vaults](#team-vaults)
- [Async Client](#async-client)
- [XysqAgent](#xysqagent)
- [Tool Calling Integrations](#tool-calling-integrations)
- [Examples](#examples)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Documentation](#documentation)

---

## Core Concepts

**Memory** is the episodic layer — captures of conversations, decisions, and preferences. Each memory is searchable, taggable, and retrievable across sessions.

**Knowledge** is the structural layer — indexed sources (links, code, quotes, documents) that feed into a persistent knowledge base your agents can query.

**Vaults** scope both layers. Personal vaults belong to you. Team vaults are shared across all team members and every agent they use.

The three core operations:

| Operation | What it does |
|---|---|
| `capture` | Store a memory permanently |
| `surface` | Retrieve relevant memories for a query |
| `synthesize` | Ask a natural language question answered from memory |

---

## API Reference

### Memory

```python
from xysq import Xysq

client = Xysq()  # reads XYSQ_API_KEY from env
```

#### `client.memory.capture(content, *, context, tags, significance, scope, memory_type, document_id, metadata, timestamp)`

Store a memory.

```python
result = client.memory.capture(
    content="Team decided to use PostgreSQL for the main database",
    context="Architecture review — 2026-04-15",
    tags=["architecture", "database"],
    significance="high",  # "low" | "normal" | "high"
    scope="permanent",    # "permanent" | "session"
)
print(result.memory_id)  # unique ID for this memory
print(result.status)     # "pending" | "processing" | "completed"
```

#### `client.memory.surface(query, *, budget, types, intent, domain, scope, memory_type, agent_filter)`

Retrieve the most relevant memories for a query.

```python
memories = client.memory.surface(
    "coding preferences and style",
    budget="mid",  # "low" | "mid" | "high" — controls recall depth
)
for m in memories:
    print(f"[{m.id}] {m.text}")
    print(f"  tags: {m.tags}")
```

#### `client.memory.synthesize(query, *, budget, response_schema, write_back)`

Answer a natural language question from your memory bank.

```python
result = client.memory.synthesize(
    "What are the team's engineering standards?",
    budget="mid",
    write_back=False,  # if True, saves the synthesis as a new memory
)
print(result.answer)
print(result.confidence)  # "high" | "medium" | "low"
print(result.sources)     # list of memory IDs used
```

#### `client.memory.list(limit, agent_filter)`

List stored memories.

```python
memories = client.memory.list(limit=20)
for m in memories:
    print(m.text)
```

#### `client.memory.delete(memory_id)`

Delete a memory by ID.

```python
client.memory.delete("mem_abc123")
```

#### `client.memory.status(memory_id)` / `client.memory.wait(memory_id)`

Check or wait for indexing to complete.

```python
# Non-blocking check
status = client.memory.status(result.memory_id)
print(status.status)  # "pending" | "processing" | "completed" | "failed"

# Block until indexed (or timeout)
final = client.memory.wait(result.memory_id, timeout=30.0)
```

---

### Knowledge Base

Add external sources — links, code snippets, quotes — to your persistent knowledge base.

```python
# Index a URL
source = client.knowledge.add(
    type="link",
    url="https://docs.python.org/3/library/typing.html",
    title="Python typing module",
    session_context="Researching type annotations",
)

# Add a code snippet
source = client.knowledge.add(
    type="code",
    content="def retry(fn, max_attempts=3): ...",
    title="Retry utility",
    confidence="high",  # "low" | "medium" | "high"
)

# Add a text quote / decision record
source = client.knowledge.add(
    type="quote",
    content="ADR-12: All services must expose /healthz and /readyz endpoints.",
    title="ADR-12: Health Check Standards",
)

# Wait for indexing
client.knowledge.wait(source.source_id, timeout=60.0)

# List all sources
sources = client.knowledge.list(limit=20, status="indexed")
for s in sources:
    print(f"[{s.source_id}] {s.type}: {s.title}")
```

Supported `type` values: `"link"`, `"code"`, `"quote"`

Once indexed, knowledge sources are automatically surfaced through `memory.surface()` and `memory.synthesize()`.

---

### Team Vaults

Share memory and knowledge across your entire team. Every team member and every agent they use reads from and writes to the same vault.

```python
import os
from xysq import Xysq

client = Xysq()
team = client.team(os.environ["XYSQ_TEAM_ID"])

# Capture a team decision
team.memory.capture(
    content="API versioning follows semver; breaking changes require RFC",
    tags=["api", "standards"],
    significance="high",
)

# Any team member's agent can surface this
memories = team.memory.surface("API versioning policy")

# Team knowledge base works the same way
team.knowledge.add(
    type="quote",
    content="Sprint cadence: 2 weeks. Retros every other Friday.",
    title="Team Process — Sprint Cadence",
)

# Synthesize from team context
result = team.memory.synthesize("What are our engineering standards?")
print(result.answer)
```

Set up and manage teams at [app.xysq.ai](https://app.xysq.ai) or see the [Teams documentation](https://docs.xysq.ai/features/teams).

---

## Async Client

`AsyncXysq` is the async-native client. The sync `Xysq` client wraps it with a background event loop — both expose identical interfaces.

```python
import asyncio
from xysq import AsyncXysq

async def main():
    async with AsyncXysq() as client:
        await client.memory.capture("Async operations are elegant")

        memories = await client.memory.surface("async patterns")
        for m in memories:
            print(m.text)

        result = await client.memory.synthesize("What do I know about async?")
        print(result.answer)

asyncio.run(main())
```

---

## XysqAgent

`XysqAgent` wraps any [LiteLLM](https://github.com/BerriAI/litellm)-compatible model with automatic memory retrieval and capture. Every `chat()` call surfaces relevant memories, injects them into the system prompt, calls the LLM, and captures the exchange.

```bash
pip install 'xysq[agent]'
```

```python
from xysq import Xysq, XysqAgent

client = Xysq()

agent = XysqAgent(
    client=client,
    model="gpt-4o-mini",        # any LiteLLM model string
    api_key="sk-...",
    system_prompt="You are a helpful coding assistant.",
    context_strategy="surface", # "surface" | "synthesize" | "both" | "none"
    surface_budget="low",
)

# Memory persists — a fresh agent instance picks up where the last left off
reply = agent.chat("I prefer functional programming patterns over OOP.")
print(reply)

reply = agent.chat("What are my coding preferences?")
print(reply)
```

### Context Strategies

| Strategy | Behaviour |
|---|---|
| `"surface"` | Retrieves raw memory items relevant to the current message |
| `"synthesize"` | Runs a synthesis query and injects the answer as context |
| `"both"` | Runs both and injects both into the prompt |
| `"none"` | No automatic context injection |
| Custom | Any callable matching the `ContextStrategy` protocol |

### Custom Strategy

```python
from xysq import ContextStrategy

class AdaptiveStrategy:
    """Synthesize on first turn for overview, surface on follow-ups for precision."""

    def __call__(self, client, message, turn_count, history):
        if turn_count == 1:
            result = client.memory.synthesize(message, budget="low")
            return f"[overview] {result.answer}" if result.answer else ""
        else:
            items = client.memory.surface(message, budget="low")
            return "\n".join(f"- {m.text}" for m in items)

agent = XysqAgent(
    client=client,
    model="gpt-4o-mini",
    api_key="sk-...",
    context_strategy=AdaptiveStrategy(),
)
```

---

## Tool Calling Integrations

Let the LLM decide when to capture, surface, and synthesize — using native tool-calling.

### LiteLLM

```python
from xysq import Xysq
from xysq.integrations.litellm import XysqLiteLLMTools
import litellm

client = Xysq()
tools = XysqLiteLLMTools(client)

messages = [
    {"role": "system", "content": "You have persistent memory tools. Use them proactively."},
    {"role": "user", "content": "I always want Python examples with type hints."},
]

response = litellm.completion(model="gpt-4o-mini", messages=messages, tools=tools.definitions)
# Execute any tool calls returned by the model
results = tools.execute(response.choices[0].message.tool_calls)
```

### Anthropic

```python
from xysq.integrations.anthropic import XysqAnthropicTools
import anthropic

tools = XysqAnthropicTools(client)
# tools.definitions → Anthropic-format tool schemas
# tools.execute(tool_use_blocks) → tool results
```

Available tools exposed to the LLM:

- `xysq_capture` — store a memory
- `xysq_surface` — retrieve relevant memories
- `xysq_synthesize` — ask a question from memory
- `xysq_list_memories` — list recent memories
- `xysq_delete_memory` — delete a memory
- `xysq_add_knowledge` — add a knowledge source
- `xysq_list_knowledge` — list knowledge sources

---

## Examples

All examples load credentials from `.env`:

```
XYSQ_API_KEY=xysq_...
XYSQ_TEAM_ID=...         # for team examples
OPENAI_API_KEY=sk-...    # for LiteLLM examples
```

| File | What it demonstrates |
|---|---|
| [`01_basic_memory.py`](examples/01_basic_memory.py) | Capture, surface, synthesize, list — the core loop |
| [`02_chatbot_with_memory.py`](examples/02_chatbot_with_memory.py) | Multi-turn chatbot with LiteLLM and persistent memory |
| [`03_team_memory.py`](examples/03_team_memory.py) | Two agents sharing a team vault |
| [`04_knowledge_base.py`](examples/04_knowledge_base.py) | Indexing links, code snippets, and quotes |
| [`05_agent_with_tools.py`](examples/05_agent_with_tools.py) | LLM-driven tool-calling loop with xysq tools |
| [`06_xysq_agent.py`](examples/06_xysq_agent.py) | XysqAgent with surface, synthesize, and custom strategies |

Run any example:

```bash
cd python_sdk
pip install 'xysq[agent]'
python examples/01_basic_memory.py
```

---

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `XYSQ_API_KEY` | — | Your xysq API key (required) |
| `XYSQ_BASE_URL` | `https://api.xysq.ai` | Override for self-hosted or staging |

You can also pass credentials directly:

```python
client = Xysq(
    api_key="xysq_...",
    timeout=60.0,      # request timeout in seconds
    max_retries=3,     # retries on 429 / 5xx with exponential backoff
)
```

---

## Error Handling

All SDK errors inherit from `XysqError`:

```python
from xysq import Xysq, AuthError, QuotaError, NotFoundError, RetryError, TimeoutError

try:
    client.memory.capture("important note")
except AuthError:
    print("Invalid or expired API key")
except QuotaError:
    print("Memory quota exceeded — delete some memories or upgrade")
except RetryError as e:
    print(f"All retries exhausted: {e}")
except TimeoutError:
    print("Request timed out")
```

The HTTP client retries automatically on `429`, `500`, `502`, `503`, `504` with exponential backoff (0.5s base, capped at 8s, with 25% jitter). `Retry-After` headers are respected on 429 responses.

---

## Documentation

Full documentation at **[docs.xysq.ai](https://docs.xysq.ai)**:

- [SDK — Getting Started](https://docs.xysq.ai/sdk/getting-started)
- [Memory operations](https://docs.xysq.ai/sdk/memory)
- [Knowledge Base](https://docs.xysq.ai/sdk/knowledge)
- [Team Vaults](https://docs.xysq.ai/sdk/teams)
- [XysqAgent & Strategies](https://docs.xysq.ai/sdk/agent)
- [Tool Calling Integrations](https://docs.xysq.ai/sdk/integrations)
- [Teams feature overview](https://docs.xysq.ai/features/teams)
- [Knowledge Base feature overview](https://docs.xysq.ai/features/knowledge-base)

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built by [xysq](https://xysq.ai). Get started at [app.xysq.ai](https://app.xysq.ai/login).*
