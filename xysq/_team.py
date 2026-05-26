"""Team-scoped view — wraps memory + organise with auto team_id injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from xysq.memory import MemoryNamespace
from xysq.organise import OrganiseNamespace

if TYPE_CHECKING:
    from xysq._http import AsyncHTTPClient


class TeamScope:
    def __init__(self, http: AsyncHTTPClient, team_id: str) -> None:
        self.memory = MemoryNamespace(http, team_id=team_id)
        self.organise = OrganiseNamespace(http, team_id=team_id)
