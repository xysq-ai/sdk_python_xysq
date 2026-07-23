"""
Example 04 -- XysqAgent (batteries included)

If you don't want to run the tool loop yourself, XysqAgent wraps a LiteLLM model
and does pull-before / push-after automatically on every chat() call, scoped to
one vault. Memory persists across instances -- a fresh agent on the same vault
already knows.

Setup:
    pip install 'xysq[agent]' litellm
    Create a .env with:
        XYSQ_API_KEY=xysq_...        # an AGENT-class key
        ANTHROPIC_API_KEY=sk-ant-... # (or the key for LITELLM_MODEL)
"""

import os

from dotenv import load_dotenv

from xysq import Xysq, XysqAgent

load_dotenv()

MODEL = os.environ.get("LITELLM_MODEL", "claude-sonnet-4-20250514")
LLM_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY", "")


def main() -> None:
    with Xysq() as client:
        vault = client.vaults.create("Agent Demo")

        agent = XysqAgent(
            client=client,
            vault_id=vault.vault_id,
            model=MODEL,
            api_key=LLM_KEY,
            system_prompt="You are a concise, helpful assistant.",
        )

        # turn 1 teaches; the exchange is pushed automatically
        print("User: I prefer tabs over spaces in Python.")
        print("Assistant:", agent.chat("I prefer tabs over spaces in Python."), "\n")

        # a fresh agent on the SAME vault recalls it (pull happens automatically)
        agent2 = XysqAgent(
            client=client, vault_id=vault.vault_id, model=MODEL, api_key=LLM_KEY,
            system_prompt="You are a concise, helpful assistant.",
        )
        print("User (new session): what's my Python indentation preference?")
        print("Assistant:", agent2.chat("What's my Python indentation preference?"))

        client.vaults.delete(vault.vault_id)
    print("\nDone.")


if __name__ == "__main__":
    main()
