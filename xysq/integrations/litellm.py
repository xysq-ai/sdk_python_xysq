"""LiteLLM adapter for xysq memory tools.

Exposes xysq memory as OpenAI-compatible function-calling tool definitions,
which LiteLLM accepts for any model (GPT, Claude, Gemini, Mistral, etc.).

Usage::

    from xysq import Xysq
    from xysq.integrations.litellm import XysqLiteLLMTools
    import litellm

    client = Xysq(api_key="xysq_...")
    tools = XysqLiteLLMTools(client)

    messages = [{"role": "user", "content": "What are my coding preferences?"}]

    while True:
        response = litellm.completion(
            model="gpt-4o",
            messages=messages,
            tools=tools.definitions,
        )
        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        tool_calls = msg.tool_calls
        if not tool_calls:
            print(msg.content)
            break

        tool_results = tools.execute(tool_calls)
        messages.extend(tool_results)
"""

from __future__ import annotations

import json
from typing import Any

from xysq.integrations._base import TOOLS


def _dispatch(client: Any, name: str, args: dict[str, Any]) -> Any:
    """Dispatch a tool call to the appropriate sync client method.

    If ``team_id`` is present in args, operations are scoped to that team.
    This function is module-level so other adapters (e.g. Anthropic) can
    reuse it.

    Args:
        client: A sync ``Xysq`` client instance.
        name:   Canonical tool name (e.g. ``"xysq_capture"``).
        args:   Tool call arguments dict.

    Returns:
        JSON-serialisable result.
    """
    # Resolve team scoping
    team_id = args.pop("team_id", None)
    scoped = client.team(team_id) if team_id else client

    if name == "xysq_capture":
        result = scoped.memory.capture(
            content=args["content"],
            context=args.get("context"),
            tags=args.get("tags"),
            significance=args.get("significance", "normal"),
            scope=args.get("scope", "permanent"),
        )
        return result.model_dump()

    if name == "xysq_surface":
        items = scoped.memory.surface(
            query=args["query"],
            budget=args.get("budget", "mid"),
            types=args.get("types"),
            agent_filter=args.get("agent_filter"),
        )
        return [item.model_dump() for item in items]

    if name == "xysq_synthesize":
        result = scoped.memory.synthesize(
            query=args["query"],
            budget=args.get("budget", "mid"),
        )
        return result.model_dump()

    if name == "xysq_list_memories":
        items = scoped.memory.list(
            limit=args.get("limit", 20),
            agent_filter=args.get("agent_filter"),
        )
        return [item.model_dump() for item in items]

    if name == "xysq_delete_memory":
        result = scoped.memory.delete(memory_id=args["memory_id"])
        return {"status": "deleted", **result}

    if name == "xysq_add_knowledge":
        result = scoped.knowledge.add(
            type=args["type"],
            content=args.get("content"),
            url=args.get("url"),
            title=args.get("title"),
        )
        return result.model_dump()

    if name == "xysq_list_knowledge":
        items = scoped.knowledge.list(
            limit=args.get("limit", 20),
            status=args.get("status"),
            type=args.get("type"),
        )
        return [item.model_dump() for item in items]

    return {"error": f"Unknown tool: {name}"}


class XysqLiteLLMTools:
    """xysq memory tools in OpenAI / LiteLLM function-calling format.

    ``definitions`` -- pass directly to ``litellm.completion(tools=...)``.
    ``execute()``   -- dispatch tool calls returned by the model.
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
        """OpenAI-compatible tool definitions for all xysq tools."""
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
        """Execute a list of tool calls returned by LiteLLM / OpenAI.

        Returns a list of ``{"role": "tool", "tool_call_id": ..., "content": ...}``
        dicts ready to be appended to the messages list.
        """
        results: list[dict[str, Any]] = []
        for call in tool_calls:
            name = call.function.name
            args: dict[str, Any] = json.loads(call.function.arguments or "{}")
            content = _dispatch(self._client, name, args)
            results.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(content),
            })
        return results
