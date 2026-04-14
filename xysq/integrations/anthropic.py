"""Anthropic (Claude) adapter for xysq memory tools.

Exposes xysq memory as Anthropic tool_use definitions.

Usage::

    import anthropic
    from xysq import Xysq
    from xysq.integrations.anthropic import XysqAnthropicTools

    xysq_client = Xysq(api_key="xysq_...")
    tools = XysqAnthropicTools(xysq_client)
    ac = anthropic.Anthropic(api_key="sk-ant-...")

    messages = [{"role": "user", "content": "What are my coding preferences?"}]

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
    """xysq memory tools in Anthropic tool_use format.

    ``definitions`` -- pass directly to ``anthropic.messages.create(tools=...)``.
    ``execute()``   -- dispatch tool_use blocks returned by Claude.
    """

    def __init__(self, client: Any, team_id: str | None = None) -> None:
        self._client = client
        self._team_id = team_id
        # If team_id provided at construction, use team-scoped client
        if team_id is not None:
            self._scoped = client.team(team_id)
        else:
            self._scoped = client

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

            content = _dispatch(self._client, name, args)
            results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": json.dumps(content),
            })
        return results
