"""
Example 04 -- Knowledge Base

Add different types of knowledge sources (link, code snippet, quote),
list them, then surface from memory to show knowledge integration.

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
        # ── 1. Add a URL source ──────────────────────────────────────
        print("=== Adding Knowledge Sources ===")

        source = client.knowledge.add(
            type="link",
            url="https://docs.python.org/3/library/typing.html",
            title="Python typing module docs",
            session_context="Researching type annotation best practices",
        )
        print(f"Link source added: id={source.source_id}, status={source.status}")

        # ── 2. Add a code snippet ────────────────────────────────────
        source = client.knowledge.add(
            type="code",
            content="""\
def retry(fn, max_attempts=3, backoff=1.0):
    \"\"\"Retry a function with exponential backoff.\"\"\"
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            time.sleep(backoff * (2 ** attempt))""",
            title="Retry utility pattern",
            session_context="Common utility functions we use across projects",
            confidence="high",
        )
        print(f"Code added: id={source.source_id}, status={source.status}")

        # ── 3. Add a quote ───────────────────────────────────────────
        source = client.knowledge.add(
            type="quote",
            content=(
                "Architecture Decision Record #12: "
                "All new services must expose health check endpoints at /healthz. "
                "Readiness probes at /readyz. Liveness checks must complete in <200ms."
            ),
            title="ADR-12: Health Check Standards",
            confidence="high",
        )
        print(f"Quote added: id={source.source_id}, status={source.status}")

        # ── 4. List knowledge sources ────────────────────────────────
        print("\n=== Knowledge Sources ===")

        sources = client.knowledge.list(limit=10)
        print(f"Total sources: {len(sources)}")
        for s in sources:
            print(
                f"  [{s.source_id[:8]}] type={s.type}, "
                f"title={s.title or '(none)'}, status={s.status}"
            )

        # Give the backend time to process
        time.sleep(3)

        # ── 5. Surface from memory to show knowledge integration ─────
        print("\n=== Surfacing from Memory ===")

        memories = client.memory.surface(
            "health check standards and endpoint requirements"
        )
        print(f"Found {len(memories)} relevant memories:")
        for m in memories:
            print(f"  [{m.id[:8]}] {m.text[:80]}")

        # ── 6. Synthesize from knowledge ─────────────────────────────
        print("\n=== Synthesize ===")

        synthesis = client.memory.synthesize(
            "What are the health check requirements for new services?"
        )
        print(f"Answer: {synthesis.answer}")
        print(f"Confidence: {synthesis.confidence}")

    print("\nDone.")


if __name__ == "__main__":
    main()
