"""XysqAgent -- a memory-aware wrapper around any LiteLLM-compatible model.

Backed by a xysq VAULT twice over: the conversation itself lives in a server-
side THREAD (ordered, verbatim, read-your-writes -- survives restarts and is
shared across instances), and every turn is automatically promoted into the
vault's long-term memory, so future sessions remember it. On each ``chat()``
call it pulls relevant long-term context, injects it, calls the LLM, and
appends both turns to the thread.

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
        thread_id="ticket-4471",   # optional; defaults to a fresh uuid
    )

    print(agent.chat("what's our refund policy?"))

A fresh XysqAgent pointed at the same (vault_id, thread_id) resumes the SAME
conversation -- history is server state, not process state.
"""

from __future__ import annotations

import uuid
from typing import Any

_DEFAULT_SYSTEM = "You are a helpful assistant."


class XysqAgent:
    """Memory-aware agent backed by any LiteLLM-compatible model, scoped to one
    xysq vault and one server-side thread.

    Uses the **sync** ``Xysq`` client and ``litellm.completion`` (sync).

    Args:
        client:          ``Xysq`` sync client (constructed with an agent key).
        vault_id:        the vault this agent reads and writes.
        model:           any LiteLLM model string, e.g. ``"claude-sonnet-4-20250514"``.
        api_key:         API key for the LLM provider (passed to LiteLLM).
        system_prompt:   base system prompt.
        thread_id:       the conversation's id. Reuse one to RESUME a
                         conversation across processes; omit for a fresh one.
        recall:          pull long-term context before each turn (default ``True``).
        recall_limit:    max context items to pull per turn (default ``8``).
        history_turns:   how many recent turns to replay to the model (default ``24``).
    """

    def __init__(
        self,
        client: Any,
        vault_id: str,
        model: str,
        api_key: str,
        system_prompt: str = _DEFAULT_SYSTEM,
        thread_id: str | None = None,
        recall: bool = True,
        recall_limit: int = 8,
        history_turns: int = 24,
    ) -> None:
        self._client = client
        self._vault_id = vault_id
        self._model = model
        self._api_key = api_key
        self._system_prompt = system_prompt
        self.thread_id = thread_id or uuid.uuid4().hex
        self._recall = recall
        self._recall_limit = recall_limit
        self._history_turns = history_turns

    def chat(self, message: str) -> str:
        """One turn: append the user turn -> pull long-term context -> rebuild
        the window from the SERVER's thread -> call the LLM -> append the
        reply. Long-term capture is automatic (the server promotes and
        distills thread turns), so there is no explicit push here."""
        try:
            import litellm
        except ImportError as exc:
            raise ImportError(
                "XysqAgent requires litellm. Install it with: pip install 'xysq[agent]'"
            ) from exc

        # 1. the user turn is durable BEFORE the model runs: a crash mid-turn
        #    loses the reply, never the question
        self._client.threads.append(
            self._vault_id, self.thread_id, "user", message)

        # 2. long-term context (cross-thread, older than this window)
        context_text = ""
        if self._recall:
            hits = self._client.vaults.pull(
                self._vault_id, message, limit=self._recall_limit
            )
            context_text = "\n".join(f"- {h.content}" for h in hits if h.content)

        # 3. the working window comes from the SERVER, not process memory --
        #    a fresh instance on the same thread_id sees the same history
        window = self._client.threads.read(
            self._vault_id, self.thread_id, last_n=self._history_turns)
        messages = [{"role": "system", "content": self._build_system(context_text)}]
        messages += [{"role": t.role, "content": t.content} for t in window.turns]

        # 4. call the LLM
        response = litellm.completion(
            model=self._model, api_key=self._api_key, messages=messages,
        )
        assistant_text: str = response.choices[0].message.content or ""

        # 5. the reply joins the thread; the server's auto-flush promotes the
        #    conversation into long-term memory turn by turn
        self._client.threads.append(
            self._vault_id, self.thread_id, "assistant", assistant_text)

        return assistant_text

    def push(self, content: str, title: str | None = None,
             metadata: dict[str, Any] | None = None) -> Any:
        """Manually push content into the vault (e.g. a fact to remember).
        ``metadata`` passes through -- e.g. ``{"session_id": ...}`` to append
        to an existing source."""
        return self._client.vaults.push(
            self._vault_id, content, title=title, metadata=metadata)

    def pull(self, query: str, limit: int = 8) -> Any:
        """On-demand recall from the vault."""
        return self._client.vaults.pull(self._vault_id, query, limit=limit)

    def clear_history(self) -> None:
        """End this conversation: flushes it into long-term memory, then
        clears the thread's working window. The next chat() starts fresh
        (same thread_id, sequence numbers keep counting)."""
        self._client.threads.clear(self._vault_id, self.thread_id)

    def _build_system(self, context_text: str) -> str:
        """Append a ``<memory>`` block to the system prompt when context exists."""
        if not context_text:
            return self._system_prompt
        return (
            self._system_prompt
            + "\n\n<memory>\n"
            + context_text
            + "\n</memory>\n"
            + "Use the memory context when it is relevant; ignore it when not."
        )
