"""
Example 05 -- Agent with Tool Calling

Full LiteLLM tool-calling loop where the LLM decides when to
capture, surface, and synthesize using xysq tools. Two turns:
the first teaches a preference, the second tests recall.

Setup:
    pip install 'xysq[agent]' litellm
    Create a .env file with:
        XYSQ_API_KEY=xysq_...
        OPENAI_API_KEY=sk-...        # or ANTHROPIC_API_KEY, etc.
"""

import os

import litellm
from dotenv import load_dotenv

from xysq import Xysq
from xysq.integrations.litellm import XysqLiteLLMTools

load_dotenv()

MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")
MAX_TOOL_ROUNDS = 10

SYSTEM_PROMPT = """\
You are a helpful assistant with access to persistent memory tools.

When the user tells you a preference, fact, or decision, use xysq_capture
to store it. When asked about something they told you before, use
xysq_surface or xysq_synthesize to recall it.

Always use your memory tools proactively -- store important information
and retrieve context before answering questions that might relate to
past conversations.\
"""


def run_turn(
    tools: XysqLiteLLMTools,
    user_message: str,
) -> str:
    """Run a single user turn with tool-calling loop."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for round_num in range(1, MAX_TOOL_ROUNDS + 1):
        response = litellm.completion(
            model=MODEL,
            messages=messages,
            tools=tools.definitions,
        )
        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        tool_calls = msg.tool_calls
        if not tool_calls:
            # No more tool calls -- return the final text
            return msg.content or ""

        # Execute tool calls and feed results back
        print(f"  [round {round_num}: {len(tool_calls)} tool call(s)]")
        for tc in tool_calls:
            print(f"    -> {tc.function.name}({tc.function.arguments})")

        tool_results = tools.execute(tool_calls)
        messages.extend(tool_results)

    return messages[-1].get("content", "(max tool rounds reached)")


def main() -> None:
    with Xysq() as client:
        tools = XysqLiteLLMTools(client)

        # ── Turn 1: Teach a preference ───────────────────────────────
        print("=== Turn 1: Teaching a preference ===")
        print("User: I always want code examples in Python with type hints.\n")

        reply = run_turn(
            tools,
            "I always want code examples in Python with type hints.",
        )
        print(f"Assistant: {reply}\n")

        # ── Turn 2: Test recall ──────────────────────────────────────
        print("=== Turn 2: Testing recall ===")
        print("User: Can you show me how to reverse a list?\n")

        reply = run_turn(
            tools,
            "Can you show me how to reverse a list? "
            "Check my preferences first.",
        )
        print(f"Assistant: {reply}")

    print("\nDone.")


if __name__ == "__main__":
    main()
