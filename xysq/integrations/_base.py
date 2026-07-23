"""Shared tool definitions used by all framework adapters.

Two canonical tools that map to the vault API: pull context in, push context
out. The vault is fixed per adapter instance (bound at construction), so it is
NOT a tool argument -- the model just decides WHEN to remember and recall, not
WHICH vault.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Canonical tool schemas (source of truth -- adapters convert from this)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "xysq_pull_context",
        "description": (
            "Pull relevant context from the user's memory before answering. "
            "Call this at the start of a task, and whenever the user references "
            "something you don't have in the conversation (a past decision, a "
            "preference, 'the auth bug'). Returns the assembled context."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What you need, in plain words. Omit for the most recent context.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max items to return (default 8).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "xysq_push_context",
        "description": (
            "Push what happened into the user's memory so it persists across "
            "sessions. Call this after a meaningful exchange -- a decision, a "
            "correction, a fact worth keeping. Send it VERBATIM (turn by turn, "
            "'user: ...' / 'agent: ...'), do NOT summarize -- the server extracts "
            "the details."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The verbatim content to remember, turn by turn.",
                },
                "title": {
                    "type": "string",
                    "description": "Optional short label for this memory.",
                },
            },
            "required": ["content"],
        },
    },
]
