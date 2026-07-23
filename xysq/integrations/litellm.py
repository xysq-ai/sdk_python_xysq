"""LiteLLM adapter for xysq memory.

Exposes xysq as OpenAI-compatible function-calling tools so YOUR OWN LiteLLM
loop gets memory -- you keep control of the model, the messages, and the loop;
xysq is just two tools the model can call (pull context, push context), bound to
one vault. Works for any LiteLLM model (GPT, Claude, Gemini, Mistral, ...).

Usage::

    from xysq import Xysq
    from xysq.integrations.litellm import XysqLiteLLMTools
    import litellm

    client = Xysq(api_key="xysq_agent_...")          # an agent-class key
    vault = client.vaults.create("Support Bot")
    tools = XysqLiteLLMTools(client, vault.vault_id)  # bind the vault

    messages = [{"role": "user", "content": "what's our refund policy?"}]
    while True:
        response = litellm.completion(
            model="gpt-4o",
            messages=messages,
            tools=tools.definitions,
        )
        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            print(msg.content)
            break
        messages.extend(tools.execute(msg.tool_calls))
"""

from __future__ import annotations

import json
from typing import Any

from xysq.integrations._base import TOOLS


def _dispatch(client: Any, vault_id: str, name: str, args: dict[str, Any]) -> Any:
    """Dispatch a tool call to the vault API. Module-level so other adapters
    (Anthropic) reuse it. The vault is bound by the adapter, not the model."""
    if name == "xysq_pull_context":
        hits = client.vaults.pull(
            vault_id, args.get("query"), limit=args.get("limit", 8)
        )
        return [h.model_dump() for h in hits]

    if name == "xysq_push_context":
        result = client.vaults.push(
            vault_id, args["content"], title=args.get("title")
        )
        return result.model_dump()

    return {"error": f"Unknown tool: {name}"}


class XysqLiteLLMTools:
    """xysq vault tools in OpenAI / LiteLLM function-calling format.

    ``definitions`` -- pass to ``litellm.completion(tools=...)``.
    ``execute()``   -- dispatch tool calls the model returned.

    The ``vault_id`` is bound here, so the model decides WHEN to remember/recall,
    never WHICH vault.
    """

    def __init__(self, client: Any, vault_id: str) -> None:
        self._client = client
        self._vault_id = vault_id

    @property
    def definitions(self) -> list[dict[str, Any]]:
        """OpenAI-compatible tool definitions for the xysq vault tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in TOOLS
        ]

    def execute(self, tool_calls: list[Any]) -> list[dict[str, Any]]:
        """Execute tool calls returned by LiteLLM / OpenAI. Returns
        ``{"role": "tool", "tool_call_id": ..., "content": ...}`` dicts ready to
        append to the messages list."""
        results: list[dict[str, Any]] = []
        for call in tool_calls:
            name = call.function.name
            args: dict[str, Any] = json.loads(call.function.arguments or "{}")
            content = _dispatch(self._client, self._vault_id, name, args)
            results.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(content),
            })
        return results
