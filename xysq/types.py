"""Pydantic v2 models for xysq SDK responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


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
