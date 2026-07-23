"""
Example 02 -- LiteLLM with memory tools

Your own LiteLLM loop, plus two xysq tools (xysq_pull_context / xysq_push_context)
bound to a vault. The MODEL decides when to remember and recall; you keep the
model, the messages, and the loop. Two turns: the first teaches a preference,
the second tests recall in a fresh conversation.

Setup:
    pip install 'xysq[agent]' litellm
    Create a .env with:
        XYSQ_API_KEY=xysq_...        # an AGENT-class key
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
You are a helpful assistant with persistent memory.

Use xysq_pull_context at the start of a task to recall what you know about the
user. Use xysq_push_context after a meaningful exchange to remember it -- send
it verbatim, turn by turn, do not summarize.\
"""


def run_turn(tools: XysqLiteLLMTools, user_message: str) -> str:
    """One user turn, running the tool-calling loop to completion."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for round_num in range(1, MAX_TOOL_ROUNDS + 1):
        response = litellm.completion(model=MODEL, messages=messages, tools=tools.definitions)
        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return msg.content or ""

        print(f"  [round {round_num}: {len(msg.tool_calls)} tool call(s)]")
        for tc in msg.tool_calls:
            print(f"    -> {tc.function.name}({tc.function.arguments})")
        messages.extend(tools.execute(msg.tool_calls))

    return "(max tool rounds reached)"


def main() -> None:
    with Xysq() as client:
        vault = client.vaults.create("LiteLLM Demo")
        tools = XysqLiteLLMTools(client, vault.vault_id)  # bind the vault

        print("=== Turn 1: teach a preference ===")
        print("User: I always want Python code examples with type hints.\n")
        print("Assistant:", run_turn(tools, "I always want Python code examples with type hints."), "\n")

        print("=== Turn 2: test recall (fresh conversation) ===")
        print("User: show me how to reverse a list.\n")
        print("Assistant:", run_turn(
            tools, "Show me how to reverse a list. Check my preferences first."
        ))

        client.vaults.delete(vault.vault_id)
    print("\nDone.")


if __name__ == "__main__":
    main()
