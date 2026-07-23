"""XysqAgent -- a memory-aware wrapper around any LiteLLM-compatible model.

Backed by a xysq VAULT: on every ``chat()`` call it pulls relevant context from
the vault, injects it into the system prompt, calls the LLM via
``litellm.completion``, and pushes the exchange back so the next session
remembers it. Memory persists across instances -- a fresh XysqAgent pointed at
the same vault sees everything prior turns pushed.

Usage::

    from xysq import Xysq, XysqAgent

    client = Xysq(api_key="xysq_agent_...")   # an agent-class key
    vault = client.vaults.create("Support Bot")

    agent = XysqAgent(
        client=client,
        vault_id=vault.vault_id,
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-...",
        system_prompt="You are a helpful support agent.",
    )

    print(agent.chat("what's our refund policy?"))
"""

from __future__ import annotations

from typing import Any

_DEFAULT_SYSTEM = "You are a helpful assistant."


class XysqAgent:
    """Memory-aware agent backed by any LiteLLM-compatible model, scoped to one
    xysq vault.

    Uses the **sync** ``Xysq`` client and ``litellm.completion`` (sync).

    Args:
        client:          ``Xysq`` sync client (constructed with an agent key).
        vault_id:        the vault this agent reads and writes.
        model:           any LiteLLM model string, e.g. ``"claude-sonnet-4-20250514"``.
        api_key:         API key for the LLM provider (passed to LiteLLM).
        system_prompt:   base system prompt.
        recall:          pull context before each turn (default ``True``).
        capture:         push the exchange after each turn (default ``True``).
        recall_limit:    max context items to pull per turn (default ``8``).
    """

    def __init__(
        self,
        client: Any,
        vault_id: str,
        model: str,
        api_key: str,
        system_prompt: str = _DEFAULT_SYSTEM,
        recall: bool = True,
        capture: bool = True,
        recall_limit: int = 8,
    ) -> None:
        self._client = client
        self._vault_id = vault_id
        self._model = model
        self._api_key = api_key
        self._system_prompt = system_prompt
        self._recall = recall
        self._capture = capture
        self._recall_limit = recall_limit
        self._history: list[dict[str, str]] = []

    def chat(self, message: str) -> str:
        """One turn: pull vault context -> inject -> call the LLM -> push the
        exchange back into the vault -> return the reply."""
        try:
            import litellm
        except ImportError as exc:
            raise ImportError(
                "XysqAgent requires litellm. Install it with: pip install 'xysq[agent]'"
            ) from exc

        # 1. pull relevant context from the vault
        context_text = ""
        if self._recall:
            hits = self._client.vaults.pull(
                self._vault_id, message, limit=self._recall_limit
            )
            context_text = "\n".join(f"- {h.content}" for h in hits if h.content)

        # 2. build the system prompt with a <memory> block
        system = self._build_system(context_text)

        # 3. call the LLM
        self._history.append({"role": "user", "content": message})
        response = litellm.completion(
            model=self._model,
            api_key=self._api_key,
            messages=[{"role": "system", "content": system}] + self._history,
        )
        assistant_text: str = response.choices[0].message.content or ""
        self._history.append({"role": "assistant", "content": assistant_text})

        # 4. push the exchange back verbatim so the vault remembers it
        if self._capture:
            self._client.vaults.push(
                self._vault_id,
                f"user: {message}\nagent: {assistant_text}",
            )

        return assistant_text

    def push(self, content: str, title: str | None = None) -> Any:
        """Manually push content into the vault (e.g. a fact to remember)."""
        return self._client.vaults.push(self._vault_id, content, title=title)

    def pull(self, query: str, limit: int = 8) -> Any:
        """On-demand recall from the vault."""
        return self._client.vaults.pull(self._vault_id, query, limit=limit)

    def clear_history(self) -> None:
        """Clear the in-session conversation history (the vault is unaffected)."""
        self._history = []

    def _build_system(self, context_text: str) -> str:
        """Append a ``<memory>`` block to the system prompt when context exists."""
        if not context_text:
            return self._system_prompt
        return (
            self._system_prompt
            + "\n\n<memory>\n"
            + "The following is relevant context recalled from your vault:\n"
            + context_text
            + "\n</memory>"
        )
