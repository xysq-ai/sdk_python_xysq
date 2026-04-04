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


class ReflectResult(BaseModel):
    answer: str
    query: str
