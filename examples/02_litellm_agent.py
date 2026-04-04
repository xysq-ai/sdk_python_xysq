"""
Example 02 — LiteLLM adapter

Shows how to wire xysq memory tools into a LiteLLM agent loop.
Works with any model string LiteLLM supports (GPT, Claude, Gemini, Mistral, …).

Setup:
    pip install 'xysq[agent]'
    export XYSQ_API_KEY=xysq_...
    export OPENAI_API_KEY=sk-...   # or ANTHROPIC_API_KEY / GEMINI_API_KEY
"""

import asyncio
import json
import os

import litellm

from xysq import XysqClient
from xysq.integrations.litellm import XysqLiteLLMTools


async def run_agent(user_message: str, model: str = "gpt-4o") -> str:
    api_key = os.environ["XYSQ_API_KEY"]

    async with XysqClient(api_key=api_key) as client:
        tools = XysqLiteLLMTools(client)
        messages = [{"role": "user", "content": user_message}]

        while True:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                tools=tools.definitions,
            )
            msg = response.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))

            tool_calls = msg.tool_calls
            if not tool_calls:
                return msg.content or ""

            # Execute all tool calls and feed results back
            tool_results = await tools.execute(tool_calls)
            messages.extend(tool_results)


async def main() -> None:
    # First turn — the agent will call xysq_memory_retain to store this
    print("Turn 1:")
    reply = await run_agent("Remember that I always want concise bullet-point answers.")
    print(reply)

    print("\nTurn 2 (new agent instance, same memory):")
    reply = await run_agent("How should you format your responses to me?")
    print(reply)


if __name__ == "__main__":
    asyncio.run(main())
