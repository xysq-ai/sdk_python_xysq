"""
Example 02 -- Multi-Turn Chatbot with Memory

An interactive chatbot that remembers across turns using xysq + LiteLLM.
Each turn: surface relevant memories, build a system prompt with memory
context, call the LLM, and capture the exchange.

Setup:
    pip install 'xysq[agent]' litellm
    export XYSQ_API_KEY=xysq_...
    export OPENAI_API_KEY=sk-...        # or ANTHROPIC_API_KEY, etc.

Usage:
    python 02_chatbot_with_memory.py
    Type messages and press Enter. Type 'quit' or 'exit' to stop.
"""

import os

import litellm

from xysq import Xysq

MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """\
You are a helpful assistant with persistent memory.
When you have relevant memories, use them to personalise your responses.
Be concise and friendly.\
"""


def build_system_with_memory(base_prompt: str, memory_text: str) -> str:
    """Append a <memory> block to the system prompt when context exists."""
    if not memory_text:
        return base_prompt
    return (
        base_prompt
        + "\n\n<memory>\n"
        + "The following is relevant context recalled from your memory:\n"
        + memory_text
        + "\n</memory>"
    )


def main() -> None:
    api_key = os.environ["XYSQ_API_KEY"]
    history: list[dict[str, str]] = []

    with Xysq(api_key=api_key) as client:
        print("=== xysq Memory Chatbot ===")
        print(f"Model: {MODEL}")
        print("Type 'quit' or 'exit' to stop.\n")

        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                print("Goodbye!")
                break

            # ── 1. Surface relevant memories ─────────────────────────
            memories = client.memory.surface(user_input, budget="low")
            memory_context = ""
            if memories:
                memory_context = "\n".join(f"- {m.text}" for m in memories)
                print(f"  [recalled {len(memories)} memories]")

            # ── 2. Build system prompt with memory context ───────────
            system = build_system_with_memory(SYSTEM_PROMPT, memory_context)

            # ── 3. Call the LLM ──────────────────────────────────────
            history.append({"role": "user", "content": user_input})
            messages = [{"role": "system", "content": system}] + history

            response = litellm.completion(model=MODEL, messages=messages)
            assistant_text = response.choices[0].message.content or ""

            history.append({"role": "assistant", "content": assistant_text})
            print(f"Bot: {assistant_text}\n")

            # ── 4. Capture the exchange ──────────────────────────────
            client.memory.capture(
                content=assistant_text,
                context=user_input,
                scope="permanent",
            )

    print("Session ended.")


if __name__ == "__main__":
    main()
