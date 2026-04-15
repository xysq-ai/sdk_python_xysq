"""Pydantic v2 models for xysq SDK responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MemoryItem(BaseModel):
    id: str
    text: str
    type: str | None = None
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    context: str | None = None
    document_id: str | None = None
    occurred_at: str | None = None
    source: str | None = None  # "episodic" | "wiki"


class SynthesizeResult(BaseModel):
    answer: str
    query: str = ""
    confidence: str = "medium"
    sources: list[str] = []
    wiki_context_used: bool = False


class KnowledgeSource(BaseModel):
    source_id: str
    type: str
    title: str | None = None
    status: str = "pending"
    url: str | None = None
    location: str | None = None
    confidence: str = "medium"
    auto_detected: bool = False
    preview: str | None = None
    added_at: str | None = None


class CaptureResult(BaseModel):
    status: str = "processing"
    memory_id: str = ""
    applied_tags: list[str] = []
    dropped_tags: list[str] = []
    available_tags: list[str] = []


class StatusResult(BaseModel):
    status: str  # pending | processing | completed | failed | indexed | not_found
    memory_id: str | None = None
    source_id: str | None = None
    error_msg: str | None = None
