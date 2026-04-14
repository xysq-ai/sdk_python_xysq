"""Shared tool definitions used by all framework adapters.

Seven canonical tools that map to xysq sync client operations.
All tools include an optional ``team_id`` parameter.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Canonical tool schemas (source of truth -- adapters convert from this)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "xysq_capture",
        "description": (
            "Store a memory in the user's xysq memory bank. "
            "Call this after meaningful exchanges -- user preferences, corrections, "
            "decisions, and important facts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Text to store as a memory.",
                },
                "context": {
                    "type": "string",
                    "description": "What kind of content this is, e.g. 'user preference'.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorisation.",
                },
                "significance": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "critical"],
                    "description": "Importance level of the memory (default 'normal').",
                },
                "scope": {
                    "type": "string",
                    "enum": ["permanent", "project", "session"],
                    "description": "Persistence scope (default 'permanent').",
                },
                "team_id": {
                    "type": "string",
                    "description": "Optional team ID for team-scoped operation.",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "xysq_surface",
        "description": (
            "Retrieve memories relevant to a query from the user's xysq memory. "
            "Call this at the start of any task to pull in relevant context, "
            "preferences, and historical decisions."
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
                    "description": "Restrict to memories from a specific agent.",
                },
                "team_id": {
                    "type": "string",
                    "description": "Optional team ID for team-scoped operation.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "xysq_synthesize",
        "description": (
            "Ask a question and get an answer synthesised from the user's memories. "
            "Use for high-level questions about user style, project history, or "
            "past decisions."
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
                "team_id": {
                    "type": "string",
                    "description": "Optional team ID for team-scoped operation.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "xysq_list_memories",
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
                "team_id": {
                    "type": "string",
                    "description": "Optional team ID for team-scoped operation.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "xysq_delete_memory",
        "description": "Permanently delete a memory by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "ID of the memory to delete.",
                },
                "team_id": {
                    "type": "string",
                    "description": "Optional team ID for team-scoped operation.",
                },
            },
            "required": ["memory_id"],
        },
    },
    {
        "name": "xysq_add_knowledge",
        "description": (
            "Add a knowledge source (document, URL, or snippet) to the user's "
            "xysq knowledge base."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["document", "url", "snippet"],
                    "description": "Type of knowledge source.",
                },
                "content": {
                    "type": "string",
                    "description": "Raw text content (for 'document' or 'snippet' types).",
                },
                "url": {
                    "type": "string",
                    "description": "URL to ingest (for 'url' type).",
                },
                "title": {
                    "type": "string",
                    "description": "Human-readable title for the source.",
                },
                "team_id": {
                    "type": "string",
                    "description": "Optional team ID for team-scoped operation.",
                },
            },
            "required": ["type"],
        },
    },
    {
        "name": "xysq_list_knowledge",
        "description": "List knowledge sources available to this user.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of sources to return (default 20).",
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "processing", "ready", "failed"],
                    "description": "Filter by processing status.",
                },
                "type": {
                    "type": "string",
                    "enum": ["document", "url", "snippet"],
                    "description": "Filter by knowledge type.",
                },
                "team_id": {
                    "type": "string",
                    "description": "Optional team ID for team-scoped operation.",
                },
            },
            "required": [],
        },
    },
]
