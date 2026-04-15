"""XysqAgent -- memory-aware agent wrapper with configurable context strategies.

Wraps any LiteLLM-compatible model with automatic memory retrieval and
capture.  On every ``chat()`` call it:

  1. Runs the configured context strategy to fetch relevant memories
  2. Injects retrieved context into the system prompt
  3. Calls the LLM via ``litellm.completion`` (sync)
  4. Optionally captures user messages and/or assistant responses

Memory persists across instances -- a fresh ``XysqAgent`` in a new session
will have access to everything captured by previous sessions.

Usage::

    from xysq import Xysq, XysqAgent

    client = Xysq(api_key="xysq_...")

    agent = XysqAgent(
        client=client,
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-...",
        system_prompt="You are a helpful assistant.",
        context_strategy="surface",
    )

    response = agent.chat("I prefer tabs over spaces in Python")
    print(response)
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

_DEFAULT_SYSTEM = "You are a helpful assistant."


# ---------------------------------------------------------------------------
# Context Strategy Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class ContextStrategy(Protocol):
    """Protocol for context injection strategies.

    Implementations receive the xysq sync client, the current user message,
    the turn count, and the conversation history, and return a string to
    inject into the system prompt's ``<memory>`` block.
    """

    def __call__(
        self,
        client: Any,
        message: str,
        turn_count: int,
        history: list[dict[str, str]],
    ) -> str: ...


# ---------------------------------------------------------------------------
# Built-in strategies
# ---------------------------------------------------------------------------

class SurfaceStrategy:
    """Retrieve relevant memories via ``client.memory.surface()``."""

    def __init__(self, budget: str = "low") -> None:
        self.budget = budget

    def __call__(
        self,
        client: Any,
        message: str,
        turn_count: int,
        history: list[dict[str, str]],
    ) -> str:
        items = client.memory.surface(message, budget=self.budget)
        if not items:
            return ""
        return "\n".join(f"- {m.text}" for m in items)


class SynthesizeStrategy:
    """Synthesise an answer from memories via ``client.memory.synthesize()``."""

    def __init__(self, budget: str = "low") -> None:
        self.budget = budget

    def __call__(
        self,
        client: Any,
        message: str,
        turn_count: int,
        history: list[dict[str, str]],
    ) -> str:
        result = client.memory.synthesize(message, budget=self.budget)
        if not result.answer:
            return ""
        return f"{result.answer} (confidence: {result.confidence})"


class BothStrategy:
    """Run both surface and synthesize, merge results."""

    def __init__(self, budget: str = "low") -> None:
        self.budget = budget

    def __call__(
        self,
        client: Any,
        message: str,
        turn_count: int,
        history: list[dict[str, str]],
    ) -> str:
        parts: list[str] = []

        items = client.memory.surface(message, budget=self.budget)
        if items:
            parts.append("Relevant memories:")
            parts.extend(f"- {m.text}" for m in items)

        result = client.memory.synthesize(message, budget=self.budget)
        if result.answer:
            parts.append(f"\nSynthesized: {result.answer} (confidence: {result.confidence})")

        return "\n".join(parts)


class NoneStrategy:
    """No-op strategy -- returns an empty string."""

    def __call__(
        self,
        client: Any,
        message: str,
        turn_count: int,
        history: list[dict[str, str]],
    ) -> str:
        return ""


# ---------------------------------------------------------------------------
# String shortcut → strategy class resolution
# ---------------------------------------------------------------------------

_STRATEGY_MAP: dict[str, type] = {
    "surface": SurfaceStrategy,
    "synthesize": SynthesizeStrategy,
    "both": BothStrategy,
    "none": NoneStrategy,
}


def _resolve_strategy(
    strategy: str | ContextStrategy,
    budget: str = "low",
) -> ContextStrategy:
    """Resolve a string shortcut or validate a ContextStrategy instance."""
    if isinstance(strategy, str):
        cls = _STRATEGY_MAP.get(strategy)
        if cls is None:
            raise ValueError(
                f"Unknown context strategy {strategy!r}. "
                f"Choose from: {', '.join(sorted(_STRATEGY_MAP))}."
            )
        # NoneStrategy takes no constructor args
        if cls is NoneStrategy:
            return cls()
        return cls(budget=budget)
    # Must satisfy ContextStrategy protocol
    if not callable(strategy):
        raise TypeError(
            f"context_strategy must be a string or a callable, got {type(strategy).__name__}."
        )
    return strategy


# ---------------------------------------------------------------------------
# XysqAgent
# ---------------------------------------------------------------------------

class XysqAgent:
    """Memory-aware agent backed by any LiteLLM-compatible model.

    Uses the **sync** ``Xysq`` client and ``litellm.completion`` (sync).
    When ``team_id`` is set, all memory/knowledge operations go through
    ``client.team(team_id)``.

    Args:
        client:               ``Xysq`` sync client instance.
        model:                Any LiteLLM model string, e.g. ``"claude-sonnet-4-20250514"``.
        api_key:              API key for the LLM provider (passed to LiteLLM).
        system_prompt:        Base system prompt.
        capture_strategy:     ``"auto"`` | ``"manual"`` | ``"both"``.
        capture_scope:        Scope for captured memories (default ``"project"``).
        capture_significance: Significance for captured memories (default ``"normal"``).
        context_strategy:     String shortcut or ``ContextStrategy`` instance.
        surface_budget:       Budget passed to built-in strategies.
        team_id:              Optional team ID for team-scoped operations.
    """

    def __init__(
        self,
        client: Any,
        model: str,
        api_key: str,
        system_prompt: str = _DEFAULT_SYSTEM,
        capture_strategy: str = "auto",
        capture_scope: str = "project",
        capture_significance: str = "normal",
        context_strategy: str | ContextStrategy = "surface",
        surface_budget: str = "low",
        team_id: str | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._api_key = api_key
        self._system_prompt = system_prompt
        self._capture_strategy = capture_strategy
        self._capture_scope = capture_scope
        self._capture_significance = capture_significance
        self._context_strategy = _resolve_strategy(context_strategy, budget=surface_budget)
        self._surface_budget = surface_budget
        self._team_id = team_id
        self._history: list[dict[str, str]] = []
        self._turn_count: int = 0

        # Resolve the scoped client for memory/knowledge operations
        if team_id is not None:
            self._scoped = client.team(team_id)
        else:
            self._scoped = client

    def chat(self, message: str) -> str:
        """Send a message and receive a response.

        1. Run context strategy to produce context text
        2. Build system prompt with ``<memory>`` block
        3. If capture_strategy is ``"both"``: capture user message
        4. Append to history, call ``litellm.completion()``
        5. If capture_strategy is ``"auto"`` or ``"both"``: capture assistant response
        6. Return assistant text
        """
        try:
            import litellm
        except ImportError as exc:
            raise ImportError(
                "XysqAgent requires litellm. Install it with: pip install 'xysq[agent]'"
            ) from exc

        self._turn_count += 1

        # 1. Run context strategy
        context_text = self._context_strategy(
            self._scoped, message, self._turn_count, self._history
        )

        # 2. Build system prompt with memory block
        system = self._build_system(context_text)

        # 3. If capture_strategy == "both": capture user message before LLM call
        if self._capture_strategy == "both":
            self._scoped.memory.capture(
                content=message,
                context="user message",
                scope=self._capture_scope,
                significance=self._capture_significance,
            )

        # 4. Append user message to history and call LLM
        self._history.append({"role": "user", "content": message})

        response = litellm.completion(
            model=self._model,
            api_key=self._api_key,
            messages=[{"role": "system", "content": system}] + self._history,
        )
        assistant_text: str = response.choices[0].message.content or ""

        # Append assistant response to history
        self._history.append({"role": "assistant", "content": assistant_text})

        # 5. If capture_strategy in ("auto", "both"): capture assistant response
        if self._capture_strategy in ("auto", "both"):
            self._scoped.memory.capture(
                content=assistant_text,
                context=message,
                scope=self._capture_scope,
                significance=self._capture_significance,
            )

        # 6. Return assistant text
        return assistant_text

    def capture(self, content: str, context: str | None = None) -> Any:
        """Manually capture a memory (useful when ``capture_strategy="manual"``)."""
        return self._scoped.memory.capture(
            content=content,
            context=context,
            scope=self._capture_scope,
            significance=self._capture_significance,
        )

    def synthesize(self, query: str) -> Any:
        """On-demand synthesize from memories."""
        return self._scoped.memory.synthesize(query, budget=self._surface_budget)

    def add_knowledge(self, type: str, **kwargs: Any) -> Any:
        """Convenience passthrough to ``knowledge.add()``."""
        return self._scoped.knowledge.add(type, **kwargs)

    def clear_history(self) -> None:
        """Clear the in-session conversation history (memory is unaffected)."""
        self._history = []
        self._turn_count = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_system(self, context_text: str) -> str:
        """Append a ``<memory>`` block to the system prompt when context exists."""
        if not context_text:
            return self._system_prompt
        memory_block = (
            "\n\n<memory>\n"
            "The following is relevant context recalled from your memory:\n"
            f"{context_text}\n"
            "</memory>"
        )
        return self._system_prompt + memory_block
