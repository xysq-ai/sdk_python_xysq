"""
Example 03 — Anthropic (Claude) adapter

Shows how to wire xysq memory tools into a native Claude tool_use loop
using the Anthropic Python SDK.

Setup:
    pip install 'xysq[claude]'
    export XYSQ_API_KEY=xysq_...
    export ANTHROPIC_API_KEY=sk-ant-...
"""

import asyncio
import os

import anthropic

from xysq import XysqClient
from xysq.integrations.anthropic import XysqAnthropicTools

MODEL = "claude-opus-4-6"
MAX_TOKENS = 1024


async def run_agent(user_message: str) -> str:
    xysq_key = os.environ["XYSQ_API_KEY"]
    anthropic_key = os.environ["ANTHROPIC_API_KEY"]

    async with XysqClient(api_key=xysq_key) as xysq_client:
        tools = XysqAnthropicTools(xysq_client)
        ac = anthropic.AsyncAnthropic(api_key=anthropic_key)

        messages = [{"role": "user", "content": user_message}]

        while True:
            msg = await ac.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                tools=tools.definitions,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": msg.content})

            if msg.stop_reason != "tool_use":
                # Extract the final text block
                return next(
                    (b.text for b in msg.content if hasattr(b, "text")),
                    "",
                )

            # Dispatch tool_use blocks and continue the loop
            tool_results = await tools.execute(msg.content)
            messages.append({"role": "user", "content": tool_results})


async def main() -> None:
    print("Turn 1 — storing a preference:")
    reply = await run_agent(
        "Please remember that I prefer snake_case for all variable names."
    )
    print(reply)

    print("\nTurn 2 — recalling the preference:")
    reply = await run_agent("What naming convention should I use for Python variables?")
    print(reply)


if __name__ == "__main__":
    asyncio.run(main())
