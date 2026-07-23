# xysq SDK — Examples

Install:

```bash
pip install 'xysq[agent] @ git+https://github.com/xysq-ai/sdk_python_xysq.git'
```

Create a `.env` in this directory (or the project root):

```
# xysq -- an AGENT-class key from app.xysq.ai/agents/keys
XYSQ_API_KEY=xysq_...

# LLM provider -- required for 02, 03, 04 (see the provider reference below)
OPENAI_API_KEY=sk-...
```

---

## 01 — Vaults: push and pull

**[01_vaults_basic.py](01_vaults_basic.py)**

The fundamentals, no LLM required. Create a vault, push what happened (verbatim),
wait for the background distill, and pull it back ranked.

```bash
python 01_vaults_basic.py
```

## 02 — LiteLLM with memory tools

**[02_litellm_tools.py](02_litellm_tools.py)**

Your own LiteLLM loop plus two xysq tools (`xysq_pull_context` /
`xysq_push_context`) bound to a vault. The model decides when to remember and
recall; you keep the model, messages, and loop. Two turns: teach a preference,
then test recall.

```bash
python 02_litellm_tools.py
```

Requires an LLM provider key (see the reference below).

## 03 — Anthropic SDK with memory tools

**[03_anthropic_tools.py](03_anthropic_tools.py)**

Same idea as 02, driving Claude through the Anthropic SDK directly, with the
tools in `tool_use` format.

```bash
pip install 'xysq[claude]' anthropic
python 03_anthropic_tools.py
```

Requires `ANTHROPIC_API_KEY`.

## 04 — XysqAgent (batteries included)

**[04_xysq_agent.py](04_xysq_agent.py)**

If you don't want to run the loop yourself, `XysqAgent` wraps a LiteLLM model and
does pull-before / push-after automatically on each `chat()`, scoped to a vault.
A fresh agent on the same vault recalls what earlier turns pushed.

```bash
python 04_xysq_agent.py
```

Requires an LLM provider key.

---

## Using different LLM providers

Examples 02 and 04 use [LiteLLM](https://github.com/BerriAI/litellm), which
supports any major provider. Set `LITELLM_MODEL` and the matching API key env
var; LiteLLM picks the provider from the `provider/model-name` prefix.

| Provider | API key env var | Example `LITELLM_MODEL` |
|---|---|---|
| **OpenAI** | `OPENAI_API_KEY` | `openai/gpt-4o` |
| **Anthropic** | `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4-20250514` |
| **Google Gemini** | `GEMINI_API_KEY` | `gemini/gemini-2.0-flash` |
| **Groq** | `GROQ_API_KEY` | `groq/llama3-8b-8192` |
| **Mistral** | `MISTRAL_API_KEY` | `mistral/mistral-small-latest` |
| **Cohere** | `COHERE_API_KEY` | `cohere_chat/command-a-03-2025` |
| **Azure OpenAI** | `AZURE_API_KEY` + `AZURE_API_BASE` + `AZURE_API_VERSION` | `azure/your-deployment-name` |

If `LITELLM_MODEL` is unset, the scripts default to `gpt-4o-mini` (OpenAI) — set
`OPENAI_API_KEY` and run.
