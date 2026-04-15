"""Team-scoped view — wraps memory and knowledge with auto team_id injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from xysq.knowledge import KnowledgeNamespace
from xysq.memory import MemoryNamespace

if TYPE_CHECKING:
    from xysq._http import AsyncHTTPClient


class TeamScope:
    def __init__(self, http: AsyncHTTPClient, team_id: str) -> None:
        self.memory = MemoryNamespace(http, team_id=team_id)
        self.knowledge = KnowledgeNamespace(http, team_id=team_id)
