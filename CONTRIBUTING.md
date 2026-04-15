# Contributing to the xysq Python SDK

Thanks for your interest in contributing. Whether it's a bug fix, a new community project, or an improvement to the SDK itself — we appreciate it.

---

## Getting started

1. **Fork** the repo and clone your fork
2. **Create a branch** from `main` for your changes
3. **Make your changes** and test them locally
4. **Submit a PR** using the appropriate template

---

## Types of contributions

### Community projects

Share agents, tools, integrations, or use cases you've built with the SDK.

- Create a folder under `community/` with your project name
- Include a `README.md`, working code, and a `.env.example`
- Use the **Community Project** PR template

See [community/README.md](community/README.md) for ideas and detailed guidelines.

### Bug fixes

- Open an issue first describing the bug and how to reproduce it
- Reference the issue in your PR
- Include a minimal reproduction if possible

### SDK improvements

- Open an issue or discussion first to align on the approach
- Keep changes focused — one concern per PR
- Don't break the public API without discussion

---

## Development setup

```bash
# Clone your fork
git clone https://github.com/<your-username>/sdk_python_xysq.git
cd sdk_python_xysq

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode with all extras
pip install -e '.[all]'
```

Create a `.env` file for running examples:

```
XYSQ_API_KEY=xysq_...
```

---

## Code style

- Python 3.11+
- Type hints on all public functions
- Use `from __future__ import annotations` for forward references
- Follow existing patterns in the codebase — if you're unsure, look at a similar file
- No unnecessary dependencies — the core SDK only depends on `httpx`, `pydantic`, and `python-dotenv`

---

## Commit messages

Keep them short and descriptive:

```
fix: handle empty response from knowledge/list
feat: add tags() method to memory namespace
docs: update quickstart with agent_name example
community: add slack-memory-bot project
```

---

## Pull request guidelines

- **One concern per PR** — don't mix a bug fix with a new feature
- **Describe what and why** — not just what you changed, but why it matters
- **Test your changes** — run the relevant examples or write a test
- **Don't commit secrets** — no API keys, tokens, or credentials
- **Keep diffs clean** — don't reformat code you didn't change

---

## Reporting issues

- Use GitHub Issues
- Include: what you expected, what happened, steps to reproduce
- Include your Python version and SDK version (`pip show xysq`)

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
