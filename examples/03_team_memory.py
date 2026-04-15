"""
Example 03 -- Team Memory

Two "agents" sharing a team vault. Agent 1 captures a team decision.
Agent 2 surfaces and synthesizes team context. Both operate through
the same team-scoped client.

Setup:
    pip install xysq
    Create a .env file with:
        XYSQ_API_KEY=xysq_...
        XYSQ_TEAM_ID=team_...
"""

import os
import time

from dotenv import load_dotenv

from xysq import Xysq

load_dotenv()


def main() -> None:
    team_id = os.environ["XYSQ_TEAM_ID"]

    with Xysq() as client:
        team = client.team(team_id)

        # ── Agent 1: Capture team decisions ──────────────────────────
        print("=== Agent 1: Capturing Team Decisions ===")

        result = team.memory.capture(
            content="Team decided to use PostgreSQL for the main database",
            context="Architecture review meeting",
            tags=["architecture", "database"],
            significance="high",
        )
        print(f"Decision 1 captured: status={result.status}")

        result = team.memory.capture(
            content="Sprint cadence is 2 weeks, retros every other Friday",
            context="Process alignment meeting",
            tags=["process", "sprint"],
        )
        print(f"Decision 2 captured: status={result.status}")

        result = team.memory.capture(
            content="API versioning follows semver; breaking changes require RFC",
            context="Engineering standards discussion",
            tags=["api", "standards"],
            significance="high",
        )
        print(f"Decision 3 captured: status={result.status}")

        # Give the backend time to index
        time.sleep(2)

        # ── Agent 2: Surface and synthesize team context ─────────────
        print("\n=== Agent 2: Retrieving Team Context ===")

        # Surface specific memories
        print("\n--- Surface: architecture decisions ---")
        memories = team.memory.surface("architecture and database decisions")
        for m in memories:
            tags_str = ", ".join(m.tags) if m.tags else "none"
            print(f"  [{m.id[:8]}] {m.text}  (tags: {tags_str})")

        # Synthesize a summary
        print("\n--- Synthesize: team engineering standards ---")
        synthesis = team.memory.synthesize(
            "What are our team's engineering standards and processes?",
            budget="mid",
        )
        print(f"  Answer: {synthesis.answer}")
        print(f"  Confidence: {synthesis.confidence}")

        # List all team memories
        print("\n--- All team memories ---")
        all_memories = team.memory.list(limit=10)
        print(f"  Total: {len(all_memories)}")
        for m in all_memories:
            print(f"  [{m.id[:8]}] {m.text[:70]}")

    print("\nDone.")


if __name__ == "__main__":
    main()
