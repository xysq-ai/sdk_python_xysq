"""
Example 01 -- Vaults: push and pull

The fundamentals. Create a vault, push what happened (verbatim), and pull it
back. Distillation runs server-side in the background, so a fresh push is
pull-able within a few seconds.

Setup:
    pip install 'xysq @ git+https://github.com/xysq-ai/sdk_python_xysq.git'
    Create a .env with:
        XYSQ_API_KEY=xysq_...        # an AGENT-class key (app.xysq.ai/agents/keys)
"""

import time

from dotenv import load_dotenv

from xysq import Xysq

load_dotenv()


def main() -> None:
    with Xysq() as client:
        # one vault per agent
        vault = client.vaults.create("Demo Vault")
        print(f"created vault {vault.vault_id} ({vault.name})")

        # push verbatim -- turn by turn, do NOT summarize
        result = client.vaults.push(
            vault.vault_id,
            "user: what database do we use for the billing service\n"
            "agent: Billing runs on PostgreSQL 16, port 5432, managed by Terraform.",
            metadata={"session_id": "demo-1"},
        )
        print(f"pushed -> {result.status} ({result.id})")

        # give the background distill a moment (a few seconds for a small push)
        print("waiting for distillation...")
        time.sleep(20)

        # pull it back, ranked
        hits = client.vaults.pull(vault.vault_id, "what db does billing use")
        print(f"\npulled {len(hits)} item(s):")
        for h in hits:
            print(f"  [{h.score:.2f}] {h.content}")

        # clean up the demo vault
        client.vaults.delete(vault.vault_id)
        print("\ndeleted demo vault")


if __name__ == "__main__":
    main()
