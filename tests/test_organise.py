"""Unit tests for the Organise SDK namespace.

Focused on client-side logic: argument coercion (path vs content), the
allow-list check, the 10 MB cap, and the wire shape that ``upload_file``
sends to the backend. The backend route itself is covered separately
in backend/tests/api/test_sdk_organise_routes.py.
"""

from __future__ import annotations

import base64
from typing import Any

import pytest

from xysq.organise import (
    ALLOWED_MIME_EXACT,
    MAX_UPLOAD_BYTES,
    OrganiseNamespace,
    _is_allowed_mime,
)
from xysq.types import Folder, OrganiseFile


# ── _coerce_upload_args ───────────────────────────────────────────────────

def test_coerce_from_path(tmp_path):
    p = tmp_path / "notes.md"
    p.write_text("# hi\n", encoding="utf-8")
    raw, name, mime = OrganiseNamespace._coerce_upload_args(
        path=p, content=None, filename=None, mime_type=None,
    )
    assert raw == b"# hi\n"
    assert name == "notes.md"
    assert mime == "text/markdown"


def test_coerce_path_with_explicit_overrides(tmp_path):
    p = tmp_path / "notes.md"
    p.write_text("x", encoding="utf-8")
    raw, name, mime = OrganiseNamespace._coerce_upload_args(
        path=p, content=None, filename="renamed.md", mime_type="text/plain",
    )
    assert name == "renamed.md"
    assert mime == "text/plain"
    assert raw == b"x"


def test_coerce_path_unknown_extension_requires_explicit_mime(tmp_path):
    p = tmp_path / "thing.weird"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="could not infer mime_type"):
        OrganiseNamespace._coerce_upload_args(
            path=p, content=None, filename=None, mime_type=None,
        )


def test_coerce_content_bytes():
    raw, name, mime = OrganiseNamespace._coerce_upload_args(
        path=None, content=b"raw bytes", filename="x.pdf", mime_type="application/pdf",
    )
    assert raw == b"raw bytes"
    assert name == "x.pdf"
    assert mime == "application/pdf"


def test_coerce_content_str_encodes_utf8():
    raw, _, _ = OrganiseNamespace._coerce_upload_args(
        path=None, content="héllo", filename="x.md", mime_type="text/markdown",
    )
    assert raw == "héllo".encode("utf-8")


def test_coerce_content_requires_filename_and_mime():
    with pytest.raises(ValueError, match="filename= and mime_type= are required"):
        OrganiseNamespace._coerce_upload_args(
            path=None, content=b"x", filename=None, mime_type="text/markdown",
        )
    with pytest.raises(ValueError, match="filename= and mime_type= are required"):
        OrganiseNamespace._coerce_upload_args(
            path=None, content=b"x", filename="x.md", mime_type=None,
        )


def test_coerce_rejects_both_path_and_content(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("x")
    with pytest.raises(ValueError, match="not both"):
        OrganiseNamespace._coerce_upload_args(
            path=p, content=b"y", filename="x.md", mime_type="text/markdown",
        )


def test_coerce_rejects_neither_path_nor_content():
    with pytest.raises(ValueError, match="either path= "):
        OrganiseNamespace._coerce_upload_args(
            path=None, content=None, filename="x.md", mime_type="text/markdown",
        )


def test_coerce_rejects_missing_file(tmp_path):
    with pytest.raises(ValueError, match="is not a regular file"):
        OrganiseNamespace._coerce_upload_args(
            path=tmp_path / "ghost.md",
            content=None, filename=None, mime_type=None,
        )


# ── allow-list ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("mime", [
    "text/markdown",
    "text/plain",
    "application/pdf",
    "application/json",
    "text/csv",
    "image/png",
    "image/webp",
    "TEXT/MARKDOWN",  # case-insensitive
    "text/markdown; charset=utf-8",  # charset suffix stripped
])
def test_is_allowed_mime_accepts(mime):
    assert _is_allowed_mime(mime) is True


@pytest.mark.parametrize("mime", [
    "application/msword",
    "video/mp4",
    "application/zip",
    "",
])
def test_is_allowed_mime_rejects(mime):
    assert _is_allowed_mime(mime) is False


def test_max_upload_bytes_matches_backend():
    # If the backend ever raises this cap, both constants must move
    # together. This test exists so a one-sided bump fails loudly.
    assert MAX_UPLOAD_BYTES == 10 * 1024 * 1024


def test_markdown_is_in_allow_list():
    # The whole point of the recent backend change was to accept .md —
    # guard against accidental regression.
    assert "text/markdown" in ALLOWED_MIME_EXACT


# ── upload_file wire shape ────────────────────────────────────────────────

class _FakeHttp:
    """Captures the JSON body posted to the SDK base URL without a network call."""

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = response or {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def post(self, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((path, json))
        return self.response


@pytest.mark.asyncio
async def test_upload_file_sends_base64_and_team_id():
    http = _FakeHttp(response={
        "asset_id": "a1",
        "filename": "notes.md",
        "folder_id": "f1",
        "mime_type": "text/markdown",
        "size_bytes": 5,
        "extraction_status": "processing",
    })
    ns = OrganiseNamespace(http, team_id="team-xyz")

    result = await ns.upload_file(
        content="hello",
        filename="notes.md",
        mime_type="text/markdown",
        folder_id="f1",
    )

    assert isinstance(result, OrganiseFile)
    assert result.asset_id == "a1"

    [(path, body)] = http.calls
    assert path == "/api/sdk/organise/files/upload"
    assert body["filename"] == "notes.md"
    assert body["mime_type"] == "text/markdown"
    assert body["folder_id"] == "f1"
    assert body["team_id"] == "team-xyz"
    assert base64.b64decode(body["content_b64"]) == b"hello"


@pytest.mark.asyncio
async def test_upload_file_rejects_oversized_payload():
    """The size cap is enforced client-side so big payloads never hit the wire."""
    http = _FakeHttp()
    ns = OrganiseNamespace(http)
    huge = b"x" * (MAX_UPLOAD_BYTES + 1)
    with pytest.raises(ValueError, match="exceeds"):
        await ns.upload_file(
            content=huge, filename="big.bin", mime_type="application/pdf",
        )
    assert http.calls == []


@pytest.mark.asyncio
async def test_upload_file_rejects_disallowed_mime_client_side():
    http = _FakeHttp()
    ns = OrganiseNamespace(http)
    with pytest.raises(ValueError, match="unsupported mime_type"):
        await ns.upload_file(
            content=b"x", filename="x.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    assert http.calls == []


@pytest.mark.asyncio
async def test_list_folders_returns_typed_models():
    http = _FakeHttp(response={
        "folders": [
            {"id": "1", "name": "root", "parent_id": None, "is_system": True},
            {"id": "2", "name": "notes", "parent_id": "1", "is_system": False},
        ],
    })
    ns = OrganiseNamespace(http)
    folders = await ns.list_folders()
    assert len(folders) == 2
    assert all(isinstance(f, Folder) for f in folders)
    assert folders[0].is_system is True
    assert folders[1].parent_id == "1"


class _PathAwareHttp:
    """Returns a different stub response based on the called path."""

    def __init__(self, responses: dict[str, dict[str, Any]]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def post(self, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((path, json))
        return self._responses.get(path, {})


@pytest.mark.asyncio
async def test_team_id_threaded_into_every_call():
    http = _PathAwareHttp({
        "/api/sdk/organise/folders/list": {"folders": []},
        "/api/sdk/organise/folders/create": {"folder": {"id": "1", "name": "x"}},
    })
    ns = OrganiseNamespace(http, team_id="t-1")
    await ns.list_folders()
    await ns.create_folder("x")
    for _, body in http.calls:
        assert body["team_id"] == "t-1"
