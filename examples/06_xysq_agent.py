"""
Example 06 -- XysqAgent with Context Strategies

Demonstrates XysqAgent with three different context strategies:
  1. Surface strategy -- recalls raw memory items
  2. Synthesize strategy -- fresh agent that recalls via synthesis
  3. Custom AdaptiveStrategy -- synthesize on first turn, surface on follow-ups

Setup:
    pip install 'xysq[agent]' litellm
    Create a .env file with:
        XYSQ_API_KEY=xysq_...
        OPENAI_API_KEY=sk-...        # or ANTHROPIC_API_KEY, etc.
"""

import os
from typing import Any

from dotenv import load_dotenv

from xysq import ContextStrategy, Xysq, XysqAgent

load_dotenv()

MODEL = os.environ.get("LITELLM_MODEL", "gpt-4o-mini")
LLM_API_KEY = os.environ.get("OPENAI_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))


# ---------------------------------------------------------------------------
# Custom context strategy
# ---------------------------------------------------------------------------

class AdaptiveStrategy:
    """Synthesize on the first turn for a broad overview, then surface
    on follow-up turns for precise recall.

    Satisfies the ContextStrategy protocol.
    """

    def __init__(self, budget: str = "low") -> None:
        self.budget = budget

    def __call__(
        self,
        client: Any,
        message: str,
        turn_count: int,
        history: list[dict[str, str]],
    ) -> str:
        if turn_count == 1:
            # First turn: synthesize for a broad overview
            result = client.memory.synthesize(message, budget=self.budget)
            if not result.answer:
                return ""
            return f"[synthesized] {result.answer} (confidence: {result.confidence})"
        else:
            # Follow-up turns: surface for precise recall
            items = client.memory.surface(message, budget=self.budget)
            if not items:
                return ""
            return "\n".join(f"[surfaced] {m.text}" for m in items)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def session_1_surface(client: Xysq) -> None:
    """Surface strategy: teach preferences, then recall them."""
    print("=== Session 1: Surface Strategy ===")

    agent = XysqAgent(
        client=client,
        model=MODEL,
        api_key=LLM_API_KEY,
        system_prompt="You are a helpful coding assistant. Use recalled memories to personalise.",
        context_strategy="surface",
        surface_budget="low",
    )

    # Teach some preferences
    reply = agent.chat("I prefer functional programming patterns over OOP when possible.")
    print(f"User: I prefer functional programming patterns over OOP when possible.")
    print(f"Bot:  {reply}\n")

    reply = agent.chat("Also, I always use black for formatting and ruff for linting.")
    print(f"User: Also, I always use black for formatting and ruff for linting.")
    print(f"Bot:  {reply}\n")


def session_2_synthesize(client: Xysq) -> None:
    """Fresh agent with synthesize strategy -- recalls via synthesis."""
    print("=== Session 2: Synthesize Strategy (fresh agent) ===")

    agent = XysqAgent(
        client=client,
        model=MODEL,
        api_key=LLM_API_KEY,
        system_prompt="You are a helpful coding assistant.",
        context_strategy="synthesize",
        surface_budget="low",
    )

    reply = agent.chat("What do you know about my coding style and tooling preferences?")
    print(f"User: What do you know about my coding style and tooling preferences?")
    print(f"Bot:  {reply}\n")


def session_3_custom(client: Xysq) -> None:
    """Custom AdaptiveStrategy -- synthesize on turn 1, surface on follow-ups."""
    print("=== Session 3: Custom Adaptive Strategy ===")

    adaptive = AdaptiveStrategy(budget="low")

    agent = XysqAgent(
        client=client,
        model=MODEL,
        api_key=LLM_API_KEY,
        system_prompt="You are a helpful coding assistant with persistent memory.",
        context_strategy=adaptive,
    )

    # Turn 1: should trigger synthesize
    reply = agent.chat("Summarise what you know about me.")
    print(f"User: Summarise what you know about me.")
    print(f"Bot:  {reply}\n")

    # Turn 2: should trigger surface
    reply = agent.chat("What formatter do I use?")
    print(f"User: What formatter do I use?")
    print(f"Bot:  {reply}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    with Xysq() as client:
        session_1_surface(client)
        session_2_synthesize(client)
        session_3_custom(client)

    print("Done.")


if __name__ == "__main__":
    main()
