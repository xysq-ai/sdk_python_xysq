"""
Example 07 -- Organise: folders + file uploads

Create a folder tree, upload a Markdown note and a PDF (if you have one),
poll for extraction to complete, then surface what the model now knows.

Setup:
    pip install xysq
    Create a .env file with: XYSQ_API_KEY=xysq_...
"""

from pathlib import Path

from dotenv import load_dotenv

from xysq import Xysq

load_dotenv()


def main() -> None:
    with Xysq() as client:
        # ── 1. See what folders already exist ────────────────────────
        print("=== Current Folders ===")
        for f in client.organise.list_folders():
            indent = " " * (2 if f.parent_id else 0)
            tag = " [system]" if f.is_system else ""
            print(f"{indent}- {f.name}{tag}  id={f.id[:8]}")

        # ── 2. Create a folder under the vault root ──────────────────
        print("\n=== Creating Folder ===")
        notes = client.organise.create_folder("agent-notes")
        print(f"Created: {notes.name} (id={notes.id})")

        # ── 3. Upload a Markdown note (in-memory content) ────────────
        print("\n=== Uploading a Markdown Note ===")
        md = """\
# Sprint planning — May 13

- Ship Organise SDK
- Bump skill template to advertise organise_upload_file
- Decide: do we want folder-upload as a single call?
"""
        result = client.organise.upload_file(
            content=md,
            filename="sprint-2026-05-13.md",
            mime_type="text/markdown",
            folder_id=notes.id,
        )
        print(f"Uploaded: {result.filename}  asset_id={result.asset_id}")
        print(f"  size={result.size_bytes} bytes, status={result.extraction_status}")

        # ── 4. Upload an existing file from disk (auto-MIME, auto-name) ─
        # Skip silently if there's nothing nearby to upload — the example
        # should still run cleanly without a local PDF lying around.
        readme = Path(__file__).resolve().parent.parent / "README.md"
        if readme.is_file():
            print("\n=== Uploading a File from Disk ===")
            file = client.organise.upload_file(readme, folder_id=notes.id)
            print(f"Uploaded {file.filename} ({file.size_bytes} bytes)")

            # ── 5. Wait until extraction completes ───────────────────
            print("\n=== Waiting for Extraction ===")
            status = client.organise.wait_for_file(file.asset_id, timeout=60.0)
            print(f"Final status: {status.extraction_status}")
            if status.error_msg:
                print(f"  error: {status.error_msg}")

        # ── 6. Surface knowledge from the just-uploaded note ─────────
        print("\n=== Surfacing from Uploaded Content ===")
        memories = client.memory.surface("sprint planning May 13 organise SDK")
        print(f"Found {len(memories)} relevant memories.")
        for m in memories[:3]:
            print(f"  [{m.id[:8]}] {m.text[:120]}")

    print("\nDone.")


if __name__ == "__main__":
    main()
