"""
Example 04 — XysqAgent: zero-config memory-aware agent

XysqAgent wraps any LiteLLM model and handles memory automatically:
  - Recalls relevant memories before every response
  - Retains assistant responses after every turn

No manual tool wiring required.

Setup:
    pip install 'xysq[agent]'
    export XYSQ_API_KEY=xysq_...
    export ANTHROPIC_API_KEY=sk-ant-...   # or OPENAI_API_KEY / etc.
"""

import asyncio
import os

from xysq import XysqClient, XysqAgent


async def main() -> None:
    xysq_key = os.environ["XYSQ_API_KEY"]
    llm_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

    client = XysqClient(api_key=xysq_key)

    # ── Session 1 ──────────────────────────────────────────────────────────────
    print("=== Session 1 ===")
    agent = XysqAgent(
        client=client,
        model="claude-opus-4-6",        # swap for "gpt-4o", "gemini/gemini-2.0-flash", …
        api_key=llm_key,
        system_prompt="You are a helpful assistant.",
    )

    response = await agent.chat("I prefer tabs over spaces in all my Python projects.")
    print(f"Agent: {response}\n")

    response = await agent.chat("Also, I always write docstrings in Google style.")
    print(f"Agent: {response}\n")

    await client.aclose()

    # ── Session 2 — fresh agent instance, memory persists ─────────────────────
    print("=== Session 2 (new agent instance) ===")
    client2 = XysqClient(api_key=xysq_key)
    agent2 = XysqAgent(
        client=client2,
        model="claude-opus-4-6",
        api_key=llm_key,
    )

    response = await agent2.chat(
        "How should I format my Python code? What style do I use for docstrings?"
    )
    print(f"Agent: {response}")
    # Expected: agent knows about tabs and Google-style docstrings from Session 1

    await client2.aclose()


if __name__ == "__main__":
    asyncio.run(main())
