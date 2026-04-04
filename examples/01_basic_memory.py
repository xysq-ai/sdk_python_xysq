"""
Example 01 — Core SDK: retain + recall

Demonstrates the bare minimum: store a memory, then retrieve it.

Setup:
    pip install xysq
    export XYSQ_API_KEY=xysq_...
"""

import asyncio
import os

from xysq import XysqClient


async def main() -> None:
    api_key = os.environ["XYSQ_API_KEY"]

    async with XysqClient(api_key=api_key) as client:
        # Store a memory
        await client.memory.retain(
            content="User prefers type hints in all Python code",
            context="Code review session",
        )
        print("Memory stored.")

        # List recent memories
        memories = await client.memory.list(limit=5)
        print(f"\nRecent memories ({len(memories)}):")
        for m in memories:
            print(f"  [{m.id[:8]}] {m.text}")

        # Recall memories relevant to a query
        results = await client.memory.recall("Python coding preferences")
        print(f"\nRecall results for 'Python coding preferences' ({len(results)}):")
        for r in results:
            print(f"  - {r.text}")

        # Ask a synthesised question
        reflection = await client.memory.reflect("What are my coding preferences?")
        print(f"\nReflection: {reflection.answer}")


if __name__ == "__main__":
    asyncio.run(main())
