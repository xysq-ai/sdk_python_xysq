"""Shared tool definitions used by all framework adapters."""

from typing import Any

# ---------------------------------------------------------------------------
# Canonical tool schemas (source of truth — adapters convert from this)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "xysq_memory_recall",
        "description": (
            "Retrieve memories relevant to a query from the user's xysq memory. "
            "Call this at the start of any task to pull in relevant context, preferences, "
            "and historical decisions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query.",
                },
                "budget": {
                    "type": "string",
                    "enum": ["low", "mid", "high"],
                    "description": "Retrieval depth. 'low' is fast, 'high' is thorough.",
                },
                "types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by memory type: 'world', 'experience', 'observation'.",
                },
                "agent_filter": {
                    "type": "string",
                    "description": "Restrict to memories from a specific agent, e.g. 'claude'.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "xysq_memory_retain",
        "description": (
            "Store a memory in the user's xysq memory. "
            "Call this after meaningful exchanges — user preferences, corrections, "
            "decisions, and important facts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Text to store. Pass raw content for best extraction quality.",
                },
                "context": {
                    "type": "string",
                    "description": "What kind of content this is, e.g. 'user preference'.",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional key-value pairs for source tracking.",
                },
                "timestamp": {
                    "type": "string",
                    "description": "ISO 8601 timestamp of when this occurred. Defaults to now.",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "xysq_memory_reflect",
        "description": (
            "Ask a question and get an answer synthesised from the user's memories. "
            "Use for high-level questions about user style, project history, or past decisions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Question to answer using stored memories.",
                },
                "budget": {
                    "type": "string",
                    "enum": ["low", "mid", "high"],
                    "description": "Reasoning depth.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "xysq_memory_list",
        "description": "List recent memories stored for this user.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to return (default 20).",
                },
                "agent_filter": {
                    "type": "string",
                    "description": "Return only memories from this agent.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "xysq_memory_delete",
        "description": "Permanently delete a memory by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "ID of the memory to delete.",
                },
            },
            "required": ["memory_id"],
        },
    },
]
