"""Anthropic (Claude) adapter for xysq memory tools.

Exposes xysq memory as Anthropic tool_use definitions.

Usage::

    import anthropic
    from xysq import Xysq
    from xysq.integrations.anthropic import XysqAnthropicTools

    xysq_client = Xysq(api_key="xysq_agent_...")     # an agent-class key
    vault = xysq_client.vaults.create("Support Bot")
    tools = XysqAnthropicTools(xysq_client, vault.vault_id)   # bind the vault
    ac = anthropic.Anthropic(api_key="sk-ant-...")

    messages = [{"role": "user", "content": "what's our refund policy?"}]

    while True:
        msg = ac.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools.definitions,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": msg.content})

        if msg.stop_reason != "tool_use":
            print(next(b.text for b in msg.content if hasattr(b, "text")))
            break

        tool_results = tools.execute(msg.content)
        messages.append({"role": "user", "content": tool_results})
"""

from __future__ import annotations

import json
from typing import Any

from xysq.integrations._base import TOOLS
from xysq.integrations.litellm import _dispatch


class XysqAnthropicTools:
    """xysq vault tools in Anthropic tool_use format.

    ``definitions`` -- pass directly to ``anthropic.messages.create(tools=...)``.
    ``execute()``   -- dispatch tool_use blocks returned by Claude.

    The ``vault_id`` is bound here, so Claude decides WHEN to remember/recall,
    never WHICH vault.
    """

    def __init__(self, client: Any, vault_id: str) -> None:
        self._client = client
        self._vault_id = vault_id

    @property
    def definitions(self) -> list[dict[str, Any]]:
        """Anthropic tool definitions for all xysq tools."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            }
            for t in TOOLS
        ]

    def execute(self, content_blocks: list[Any]) -> list[dict[str, Any]]:
        """Execute tool_use blocks from a Claude response.

        Filters for ``type == "tool_use"`` blocks, dispatches each, and returns
        a list of tool_result content blocks ready to send back as a
        ``{"role": "user", "content": tool_results}`` message.
        """
        results: list[dict[str, Any]] = []
        for block in content_blocks:
            # Works with both anthropic SDK objects and plain dicts
            block_type = getattr(block, "type", None) or block.get("type")
            if block_type != "tool_use":
                continue

            tool_id = getattr(block, "id", None) or block.get("id")
            name = getattr(block, "name", None) or block.get("name")
            args = getattr(block, "input", None) or block.get("input", {})

            content = _dispatch(self._client, self._vault_id, name, args)
            results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": json.dumps(content),
            })
        return results
