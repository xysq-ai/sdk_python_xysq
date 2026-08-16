"""Pydantic v2 models for xysq SDK responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# ---- vaults (the /sdk surface) ---------------------------------------------


class Vault(BaseModel):
    """A vault -- an independent context graph addressed by vault_id."""

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


class Turn(BaseModel):
    """One turn of a thread (threads.append / threads.read)."""

    seq: int = 0
    role: str = "user"          # "user" | "assistant"
    content: str = ""
    created_at: str | None = None


class ThreadWindow(BaseModel):
    """threads.read(): the newest turns, oldest-first, ALWAYS bounded.

    ``truncated`` is explicit -- a cut window must never look like a short
    thread. ``summary`` is reserved (always None today). ``flushed_through``
    is the last seq already promoted to long-term memory."""

    turns: list[Turn] = []
    total_turns: int = 0
    truncated: bool = False
    summary: str | None = None
    flushed_through: int = 0


class ThreadInfo(BaseModel):
    """One row of threads.list()."""

    thread_id: str = ""
    total_turns: int = 0
    last_turn_at: str | None = None


class Tag(BaseModel):
    """One tag of the user's vocabulary (tags.list / tags.create)."""

    tag_id: str = ""
    name: str = ""
    created_by: str = "user"    # "system" (seeded) | "user"
    applied: int = 0            # live count of sources carrying it
    archived: bool = False      # archived tags list last; restore() revives


class SourceTagsResult(BaseModel):
    """tags.apply(): what changed and the source's resulting tag set.

    ``unknown`` names were skipped, not created -- the vocabulary is
    curated; create them first if you meant them."""

    applied: list[str] = []
    removed: list[str] = []
    unknown: list[str] = []
    tags: list[str] = []
