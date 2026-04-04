"""
LiteLLM adapter for xysq memory tools.

Exposes xysq memory as OpenAI-compatible function-calling tool definitions,
which LiteLLM accepts for any model (GPT, Claude, Gemini, Mistral, etc.).

Usage::

    from xysq import XysqClient
    from xysq.integrations.litellm import XysqLiteLLMTools
    import litellm

    client = XysqClient(api_key="xysq_...")
    tools = XysqLiteLLMTools(client)

    messages = [{"role": "user", "content": "What are my coding preferences?"}]

    while True:
        response = await litellm.acompletion(
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

        tool_results = await tools.execute(tool_calls)
        messages.extend(tool_results)
"""

from typing import Any

from xysq.client import XysqClient
from xysq.integrations._base import TOOLS


class XysqLiteLLMTools:
    """
    xysq memory tools in OpenAI / LiteLLM function-calling format.

    ``definitions`` — pass directly to ``litellm.acompletion(tools=...)``.
    ``execute()``   — dispatch tool calls returned by the model.
    """

    def __init__(self, client: XysqClient) -> None:
        self._client = client

    @property
    def definitions(self) -> list[dict[str, Any]]:
        """OpenAI-compatible tool definitions for all xysq memory tools."""
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

    async def execute(self, tool_calls: list[Any]) -> list[dict[str, Any]]:
        """
        Execute a list of tool calls returned by LiteLLM / OpenAI.

        Returns a list of ``{"role": "tool", "tool_call_id": ..., "content": ...}``
        dicts ready to be appended to the messages list.
        """
        results = []
        for call in tool_calls:
            name = call.function.name
            import json
            args: dict[str, Any] = json.loads(call.function.arguments or "{}")
            content = await _dispatch(self._client, name, args)
            results.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(content),
            })
        return results


async def _dispatch(client: XysqClient, name: str, args: dict[str, Any]) -> Any:
    if name == "xysq_memory_recall":
        items = await client.memory.recall(
            query=args["query"],
            budget=args.get("budget", "mid"),
            types=args.get("types"),
            agent_filter=args.get("agent_filter"),
        )
        return [item.model_dump() for item in items]

    if name == "xysq_memory_retain":
        await client.memory.retain(
            content=args["content"],
            context=args.get("context"),
            metadata=args.get("metadata"),
            timestamp=args.get("timestamp"),
        )
        return {"status": "stored"}

    if name == "xysq_memory_reflect":
        result = await client.memory.reflect(
            query=args["query"],
            budget=args.get("budget", "mid"),
        )
        return result.model_dump()

    if name == "xysq_memory_list":
        items = await client.memory.list(
            limit=args.get("limit", 20),
            agent_filter=args.get("agent_filter"),
        )
        return [item.model_dump() for item in items]

    if name == "xysq_memory_delete":
        count = await client.memory.delete(memory_id=args["memory_id"])
        return {"status": "deleted", "count": count}

    return {"error": f"Unknown tool: {name}"}
