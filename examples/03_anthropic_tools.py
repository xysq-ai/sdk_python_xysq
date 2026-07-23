"""
Example 03 -- Anthropic SDK with memory tools

Same idea as 02, but driving Claude through the Anthropic SDK directly instead
of LiteLLM. The xysq tools (pull_context / push_context) are exposed in
Anthropic tool_use format, bound to a vault.

Setup:
    pip install 'xysq[claude]' anthropic
    Create a .env with:
        XYSQ_API_KEY=xysq_...        # an AGENT-class key
        ANTHROPIC_API_KEY=sk-ant-...
"""

import os

import anthropic
from dotenv import load_dotenv

from xysq import Xysq
from xysq.integrations.anthropic import XysqAnthropicTools

load_dotenv()

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


def run_turn(ac: anthropic.Anthropic, tools: XysqAnthropicTools, user_message: str) -> str:
    messages: list[dict] = [{"role": "user", "content": user_message}]
    for _ in range(10):
        msg = ac.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=(
                "You are a helpful assistant with persistent memory. Use "
                "xysq_pull_context to recall, and xysq_push_context to remember "
                "(verbatim, turn by turn)."
            ),
            tools=tools.definitions,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": msg.content})
        if msg.stop_reason != "tool_use":
            return next((b.text for b in msg.content if hasattr(b, "text")), "")
        messages.append({"role": "user", "content": tools.execute(msg.content)})
    return "(max tool rounds reached)"


def main() -> None:
    with Xysq() as client:
        vault = client.vaults.create("Anthropic Demo")
        tools = XysqAnthropicTools(client, vault.vault_id)
        ac = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        print("=== Turn 1: teach a fact ===")
        print("Assistant:", run_turn(ac, tools, "Remember: our staging DB is on port 5433."), "\n")

        print("=== Turn 2: test recall ===")
        print("Assistant:", run_turn(ac, tools, "What port is the staging DB on?"))

        client.vaults.delete(vault.vault_id)
    print("\nDone.")


if __name__ == "__main__":
    main()
