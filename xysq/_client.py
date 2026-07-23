"""Async client for the xysq SDK."""

from __future__ import annotations

from xysq._config import resolve_api_key, resolve_base_url
from xysq._http import AsyncHTTPClient
from xysq.vaults import VaultsNamespace


class AsyncXysq:
    """Async client for the xysq memory API.

    Usage::

        async with AsyncXysq(api_key="xysq_agent_...") as client:
            vault = await client.vaults.create("Support Bot")
            await client.vaults.push(vault.vault_id, "user: ...\\nagent: ...")
            hits = await client.vaults.pull(vault.vault_id, "refund policy")

    Or without a context manager::

        client = AsyncXysq(api_key="xysq_agent_...")
        hits = await client.vaults.pull(vault_id, "user preferences")
        await client.aclose()
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        agent_name: str | None = None,
    ) -> None:
        key = resolve_api_key(api_key)
        base_url = resolve_base_url()
        self._http = AsyncHTTPClient(
            api_key=key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            agent_name=agent_name,
        )
        # the /sdk vault API -- agent vaults (needs an agent-class key)
        self.vaults = VaultsNamespace(self._http)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncXysq:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
