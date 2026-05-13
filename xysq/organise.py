"""Organise namespace — folders + file uploads.

Mirrors the operations exposed by the MCP ``organise_*`` tools, but over
HTTPS with an API key. Folder operations look like a small filesystem
client; ``upload_file`` accepts either a path on disk OR in-memory bytes /
text, so callers don't have to base64 things themselves.
"""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from xysq.exceptions import XysqError
from xysq.types import FileStatus, Folder, OrganiseFile

if TYPE_CHECKING:
    from xysq._http import AsyncHTTPClient

_BASE = "/api/sdk/organise"

# Hard cap mirrors the backend (assets/helpers.py). We check client-side so
# big payloads never leave the caller's process.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Mirrored from assets/helpers.ALLOWED_MIME_EXACT. Kept here so callers
# without a file extension can pick the right MIME by hand.
ALLOWED_MIME_EXACT = frozenset({
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/json",
    "text/csv",
})
ALLOWED_MIME_PREFIXES = ("image/",)


class OrganiseNamespace:
    """Async interface to xysq Organise operations."""

    def __init__(self, http: AsyncHTTPClient, team_id: str | None = None) -> None:
        self._http = http
        self._team_id = team_id

    # ── folder operations ───────────────────────────────────────────────

    async def list_folders(self) -> list[Folder]:
        """List every folder in the vault. Returns a flat array — use each
        folder's ``parent_id`` to reconstruct the tree."""
        payload: dict[str, Any] = {}
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/folders/list", json=payload)
        return [Folder.model_validate(f) for f in data.get("folders", [])]

    async def get_folder(self, folder_id: str) -> tuple[Folder, list[Folder]]:
        """Fetch one folder plus its direct children (subfolders only — files
        do not appear here; use ``list_folders`` and look up assets via the
        web UI for now)."""
        payload: dict[str, Any] = {"folder_id": folder_id}
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/folders/get", json=payload)
        folder = Folder.model_validate(data["folder"])
        children = [Folder.model_validate(c) for c in data.get("children", [])]
        return folder, children

    async def create_folder(
        self,
        name: str,
        parent_id: str | None = None,
    ) -> Folder:
        """Create a folder. Omit ``parent_id`` to nest directly under the
        vault root. Raises ``XysqError`` on name collision or invalid name.
        """
        payload: dict[str, Any] = {"name": name}
        if parent_id is not None:
            payload["parent_id"] = parent_id
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/folders/create", json=payload)
        if data.get("status") == "error":
            raise XysqError(data.get("message", "create_folder failed"))
        return Folder.model_validate(data["folder"])

    async def rename_folder(self, folder_id: str, name: str) -> None:
        """Rename a folder. System folders (root, /Chats/) cannot be renamed."""
        payload: dict[str, Any] = {"folder_id": folder_id, "name": name}
        self._inject_team(payload)
        await self._http.post(f"{_BASE}/folders/update", json=payload)

    async def move_folder(self, folder_id: str, new_parent_id: str) -> None:
        """Move a folder under a new parent (cascades children + files)."""
        payload: dict[str, Any] = {
            "folder_id": folder_id,
            "new_parent_id": new_parent_id,
        }
        self._inject_team(payload)
        await self._http.post(f"{_BASE}/folders/move", json=payload)

    async def delete_folder(
        self,
        folder_id: str,
        forget_memories: bool = False,
    ) -> int:
        """Delete a folder and everything inside it. Irreversible.

        Returns the number of files removed by the cascade. Set
        ``forget_memories=True`` to also purge extracted facts from the
        recall bank.
        """
        payload: dict[str, Any] = {
            "folder_id": folder_id,
            "forget_memories": forget_memories,
        }
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/folders/delete", json=payload)
        return int(data.get("deleted_assets", 0))

    # ── file operations ─────────────────────────────────────────────────

    async def upload_file(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        content: bytes | str | None = None,
        filename: str | None = None,
        mime_type: str | None = None,
        folder_id: str | None = None,
    ) -> OrganiseFile:
        """Upload one file into the Organise vault.

        Two call styles, pick one:

        - ``upload_file("notes.md")`` — read bytes from disk. ``filename``
          defaults to the file's basename; ``mime_type`` is inferred via
          :py:mod:`mimetypes` (override either if needed).
        - ``upload_file(content=..., filename="x.md", mime_type="text/markdown")``
          — pass in-memory bytes or a UTF-8 string.

        Bytes go inline as base64. The server proxies the upload to storage,
        so the caller doesn't need any cloud credentials. Hard cap: 10 MB.
        Allowed MIME types: text/markdown, text/plain, application/pdf,
        application/json, text/csv, image/*. Anything else returns 415.

        Raises:
            ValueError: bad arg combination, oversized payload, or unrecognised
                MIME type (caught BEFORE the bytes leave the process).
            XysqError: server rejected the upload (e.g. team auth failed).
        """
        raw, resolved_filename, resolved_mime = self._coerce_upload_args(
            path=path,
            content=content,
            filename=filename,
            mime_type=mime_type,
        )
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError(
                f"{resolved_filename} is {len(raw)} bytes, exceeds "
                f"{MAX_UPLOAD_BYTES} bytes (10 MB) cap",
            )
        if not _is_allowed_mime(resolved_mime):
            raise ValueError(
                f"unsupported mime_type {resolved_mime!r} — allowed: "
                f"text/markdown, text/plain, application/pdf, application/json, "
                f"text/csv, image/*",
            )

        payload: dict[str, Any] = {
            "filename": resolved_filename,
            "content_b64": base64.b64encode(raw).decode("ascii"),
            "mime_type": resolved_mime,
        }
        if folder_id is not None:
            payload["folder_id"] = folder_id
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/files/upload", json=payload)
        return OrganiseFile.model_validate(data)

    async def file_status(self, asset_id: str) -> FileStatus:
        """Poll the extraction status of an uploaded file."""
        payload: dict[str, Any] = {"asset_id": asset_id}
        self._inject_team(payload)
        data = await self._http.post(f"{_BASE}/files/status", json=payload)
        return FileStatus.model_validate(data)

    async def wait_for_file(
        self,
        asset_id: str,
        timeout: float = 60.0,
        interval: float = 1.0,
    ) -> FileStatus:
        """Poll until the file's extraction reaches a terminal state.

        Terminal states: ``ready``, ``failed``, ``not_found``. Returns the
        last observed status on timeout — caller can decide whether to retry.
        """
        import asyncio

        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            status = await self.file_status(asset_id)
            if status.extraction_status in ("ready", "failed", "not_found"):
                return status
            if asyncio.get_event_loop().time() >= deadline:
                return status
            await asyncio.sleep(interval)

    # ── internals ───────────────────────────────────────────────────────

    def _inject_team(self, payload: dict[str, Any]) -> None:
        if self._team_id is not None:
            payload["team_id"] = self._team_id

    @staticmethod
    def _coerce_upload_args(
        *,
        path: str | os.PathLike[str] | None,
        content: bytes | str | None,
        filename: str | None,
        mime_type: str | None,
    ) -> tuple[bytes, str, str]:
        """Normalise the two-shape call to ``(raw_bytes, filename, mime_type)``.

        Path style fills the missing fields from the file on disk; content
        style requires ``filename`` and ``mime_type`` explicitly because we
        cannot guess them from bytes.
        """
        if path is not None and content is not None:
            raise ValueError("pass either path= or content=, not both")
        if path is None and content is None:
            raise ValueError("pass either path= (read from disk) or content= (bytes/str)")

        if path is not None:
            p = Path(path)
            if not p.is_file():
                raise ValueError(f"path {p} is not a regular file")
            raw = p.read_bytes()
            resolved_filename = filename or p.name
            if mime_type is None:
                guess, _ = mimetypes.guess_type(resolved_filename)
                if guess is None:
                    # Markdown isn't always in stdlib mimetypes — fall back
                    # explicitly so .md just works.
                    if p.suffix.lower() in (".md", ".markdown"):
                        guess = "text/markdown"
                if guess is None:
                    raise ValueError(
                        f"could not infer mime_type from {p.name}; pass mime_type=…",
                    )
                resolved_mime = guess
            else:
                resolved_mime = mime_type
            return raw, resolved_filename, resolved_mime

        # content= path
        if filename is None or mime_type is None:
            raise ValueError(
                "filename= and mime_type= are required when using content=",
            )
        if isinstance(content, str):
            raw = content.encode("utf-8")
        elif isinstance(content, bytes):
            raw = content
        else:
            raise TypeError(
                f"content must be bytes or str, got {type(content).__name__}",
            )
        return raw, filename, mime_type


def _is_allowed_mime(mime_type: str) -> bool:
    mt = (mime_type or "").lower().split(";", 1)[0].strip()
    if mt in ALLOWED_MIME_EXACT:
        return True
    return any(mt.startswith(p) for p in ALLOWED_MIME_PREFIXES)
