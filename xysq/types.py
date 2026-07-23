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


class CaptureResult(BaseModel):
    status: str = "processing"
    document_id: str = ""
    applied_tags: list[str] = []
    dropped_tags: list[str] = []
    available_tags: list[str] = []


class StatusResult(BaseModel):
    status: str  # processing | completed | failed | not_found | busy
    document_id: str | None = None
    source_id: str | None = None
    error_msg: str | None = None


class Folder(BaseModel):
    """A folder in the user's (or a team's) Organise vault."""

    id: str
    name: str
    parent_id: str | None = None  # None for the vault root
    path: str | None = None
    is_system: bool = False
    chat_id: str | None = None
    owner_kind: str | None = None  # "user" | "team"
    owner_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class OrganiseFile(BaseModel):
    """An uploaded file in the Organise vault, returned by ``upload_file``."""

    asset_id: str
    filename: str
    folder_id: str
    mime_type: str
    size_bytes: int
    extraction_status: str  # pending | processing | ready | failed


class FileStatus(BaseModel):
    """Polled status of an uploaded file's extraction."""

    asset_id: str
    extraction_status: str  # pending | processing | ready | failed
    error_msg: str | None = None


# ---- vaults (the /sdk surface) ---------------------------------------------


class Vault(BaseModel):
    """An agent vault -- an independent memory addressed by vault_id."""

    vault_id: str
    name: str
    kind: str = "agent"
    is_default: bool = False


class PushResult(BaseModel):
    status: str  # "captured"
    id: str      # the captured source id


class VaultItem(BaseModel):
    """One recalled item from vault.pull()."""

    title: str | None = None
    content: str = ""
    source: str | None = None  # the layer: wiki | log | facts
    page_uuid: str | None = None
    slug: str | None = None
    score: float | None = None
