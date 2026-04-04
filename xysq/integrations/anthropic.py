"""
Anthropic (Claude) adapter for xysq memory tools.

Exposes xysq memory as Anthropic tool_use definitions.

Usage::

    import anthropic
    from xysq import XysqClient
    from xysq.integrations.anthropic import XysqAnthropicTools

    xysq = XysqClient(api_key="xysq_...")
    tools = XysqAnthropicTools(xysq)
    ac = anthropic.AsyncAnthropic(api_key="sk-ant-...")

    messages = [{"role": "user", "content": "What are my coding preferences?"}]

    while True:
        msg = await ac.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            tools=tools.definitions,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": msg.content})

        if msg.stop_reason != "tool_use":
            # Extract the final text response
            print(next(b.text for b in msg.content if hasattr(b, "text")))
            break

        tool_results = await tools.execute(msg.content)
        messages.append({"role": "user", "content": tool_results})
"""

import json
from typing import Any

from xysq.client import XysqClient
from xysq.integrations._base import TOOLS
from xysq.integrations.litellm import _dispatch


class XysqAnthropicTools:
    """
    xysq memory tools in Anthropic tool_use format.

    ``definitions`` — pass directly to ``anthropic.messages.create(tools=...)``.
    ``execute()``   — dispatch tool_use blocks returned by Claude.
    """

    def __init__(self, client: XysqClient) -> None:
        self._client = client

    @property
    def definitions(self) -> list[dict[str, Any]]:
        """Anthropic tool definitions for all xysq memory tools."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            }
            for t in TOOLS
        ]

    async def execute(self, content_blocks: list[Any]) -> list[dict[str, Any]]:
        """
        Execute tool_use blocks from a Claude response.

        Returns a list of tool_result content blocks ready to send back as a
        ``{"role": "user", "content": tool_results}`` message.
        """
        results = []
        for block in content_blocks:
            # Works with both anthropic SDK objects and plain dicts
            block_type = getattr(block, "type", None) or block.get("type")
            if block_type != "tool_use":
                continue

            tool_id = getattr(block, "id", None) or block.get("id")
            name = getattr(block, "name", None) or block.get("name")
            args = getattr(block, "input", None) or block.get("input", {})

            content = await _dispatch(self._client, name, args)
            results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": json.dumps(content),
            })
        return results
