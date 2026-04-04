"""
XysqAgent — a transparent memory-aware agent.

Wraps any LiteLLM-compatible model. On every ``chat()`` call it:
  1. Recalls relevant memories and injects them into the system prompt
  2. Calls the LLM via LiteLLM
  3. Retains the assistant response automatically

Memory persists across instances — a fresh ``XysqAgent`` in a new session
will have access to everything retained by previous sessions.

Usage::

    from xysq import XysqClient, XysqAgent

    client = XysqClient(api_key="xysq_...")

    agent = XysqAgent(
        client=client,
        model="claude-opus-4-6",
        api_key="sk-ant-...",
        system_prompt="You are a helpful assistant.",
    )

    response = await agent.chat("I prefer tabs over spaces in Python")
    print(response)

    # Later, in a new session — memory is recalled automatically
    agent2 = XysqAgent(client=client, model="claude-opus-4-6", api_key="sk-ant-...")
    response = await agent2.chat("How should I format my Python files?")
    # Agent already knows about the tabs preference
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xysq.models import MemoryItem

_DEFAULT_SYSTEM = "You are a helpful assistant."


class XysqAgent:
    """
    Memory-aware agent backed by any LiteLLM-compatible model.

    Args:
        client:           ``XysqClient`` instance for memory operations.
        model:            Any LiteLLM model string, e.g. ``"claude-opus-4-6"``,
                          ``"gpt-4o"``, ``"gemini/gemini-2.0-flash"``.
        api_key:          API key for the LLM provider (passed to LiteLLM).
        system_prompt:    Base system prompt. Recalled memories are appended
                          automatically — do not add memory instructions manually.
        retain_strategy:  ``"always"`` (default) — retain every assistant response.
                          ``"manual"`` — only retain when you call ``retain()`` yourself.
        recall_budget:    Budget passed to ``memory.recall()`` before each turn.
                          ``"low"`` is fast and suitable for most conversational use.
    """

    def __init__(
        self,
        client: Any,
        model: str,
        api_key: str,
        system_prompt: str = _DEFAULT_SYSTEM,
        retain_strategy: str = "always",
        recall_budget: str = "low",
    ) -> None:
        self._client = client
        self._model = model
        self._api_key = api_key
        self._system_prompt = system_prompt
        self._retain_strategy = retain_strategy
        self._recall_budget = recall_budget
        self._history: list[dict[str, str]] = []

    async def chat(self, message: str) -> str:
        """
        Send a message and receive a response.

        Memories relevant to the message are recalled and injected into the
        system prompt before the LLM is called. If ``retain_strategy="always"``
        the assistant response is stored after the call.

        Args:
            message: The user's message.

        Returns:
            The assistant's text response.
        """
        try:
            import litellm
        except ImportError as exc:
            raise ImportError(
                "XysqAgent requires litellm. Install it with: pip install 'xysq[agent]'"
            ) from exc

        # 1. Recall relevant memories
        memories = await self._client.memory.recall(message, budget=self._recall_budget)

        # 2. Build system prompt with injected memory context
        system = self._build_system(memories)

        # 3. Append user message to conversation history
        self._history.append({"role": "user", "content": message})

        # 4. Call LiteLLM
        response = await litellm.acompletion(
            model=self._model,
            api_key=self._api_key,
            messages=[{"role": "system", "content": system}] + self._history,
        )
        assistant_text: str = response.choices[0].message.content or ""

        # 5. Append to history
        self._history.append({"role": "assistant", "content": assistant_text})

        # 6. Retain
        if self._retain_strategy == "always":
            await self._client.memory.retain(assistant_text, context=message)

        return assistant_text

    async def retain(self, content: str, context: str | None = None) -> None:
        """Manually retain a memory (useful when ``retain_strategy="manual"``)."""
        await self._client.memory.retain(content, context=context)

    def clear_history(self) -> None:
        """Clear the in-session conversation history (memory is unaffected)."""
        self._history = []

    def _build_system(self, memories: list[Any]) -> str:
        if not memories:
            return self._system_prompt
        memory_lines = "\n".join(f"- {m.text}" for m in memories)
        memory_block = (
            "\n\n<memory>\n"
            "The following is relevant context recalled from your memory:\n"
            f"{memory_lines}\n"
            "</memory>"
        )
        return self._system_prompt + memory_block
