"""
Example 01 -- Basic Memory Operations

The "hello world" of xysq: capture a memory, surface relevant memories,
synthesize an answer, and list stored memories.

Setup:
    pip install xysq
    Create a .env file with: XYSQ_API_KEY=xysq_...
"""

import time

from dotenv import load_dotenv

from xysq import Xysq

load_dotenv()


def main() -> None:
    with Xysq() as client:
        # ── 1. Capture memories ──────────────────────────────────────
        print("=== Capture ===")

        result = client.memory.capture(
            content="User prefers type hints in all Python code",
            context="Code review session",
            tags=["python", "coding-style"],
        )
        print(f"Captured: status={result.status}, tags={result.tags_applied}")

        result = client.memory.capture(
            content="User likes dark mode across all editors and terminals",
            context="Setup preferences",
            tags=["preferences", "editor"],
            significance="high",
        )
        print(f"Captured: status={result.status}, tags={result.tags_applied}")

        result = client.memory.capture(
            content="Project deadline is end of Q2 2026",
            context="Sprint planning",
            tags=["project", "deadline"],
        )
        print(f"Captured: status={result.status}, tags={result.tags_applied}")

        # Give the backend a moment to index
        time.sleep(2)

        # ── 2. Surface relevant memories ─────────────────────────────
        print("\n=== Surface ===")

        memories = client.memory.surface("Python coding preferences")
        print(f"Found {len(memories)} memories for 'Python coding preferences':")
        for m in memories:
            print(f"  [{m.id[:8]}] {m.text}")

        # ── 3. Synthesize an answer ──────────────────────────────────
        print("\n=== Synthesize ===")

        synthesis = client.memory.synthesize(
            "What are the user's coding and editor preferences?"
        )
        print(f"Answer: {synthesis.answer}")
        print(f"Confidence: {synthesis.confidence}")
        print(f"Sources: {len(synthesis.sources)}")

        # ── 4. List recent memories ──────────────────────────────────
        print("\n=== List ===")

        all_memories = client.memory.list(limit=10)
        print(f"Total stored: {len(all_memories)}")
        for m in all_memories:
            tags_str = ", ".join(m.tags) if m.tags else "none"
            print(f"  [{m.id[:8]}] {m.text[:60]}... tags=[{tags_str}]")

    print("\nDone.")


if __name__ == "__main__":
    main()
