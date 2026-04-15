# Community Contributions

This is where the xysq community shares what they've built. If you're using the xysq SDK to power memory in your agents, tools, or workflows — we'd love to feature your work here.

---

## How to contribute

1. **Fork** this repo
2. **Create a folder** under `community/` with your project name (e.g. `community/my-memory-bot/`)
3. **Include a README** in your folder explaining what it does, how to run it, and what it demonstrates
4. **Submit a PR** with a short description

That's it. We'll review and merge.

### What to include

- A `README.md` with a clear description, setup instructions, and what the project demonstrates
- Working code that runs against the xysq SDK
- A `.env.example` showing which env vars are needed (never commit real keys)
- Keep dependencies minimal — list them in a `requirements.txt` or `pyproject.toml`

### What makes a good contribution

- **Use cases** — show how xysq memory solves a real problem (personal assistant, team knowledge bot, coding agent, support agent, etc.)
- **Integrations** — wire xysq into frameworks people use (LangChain, CrewAI, AutoGen, Haystack, etc.)
- **Patterns** — demonstrate a reusable pattern (context strategies, memory-augmented RAG, multi-agent shared memory, etc.)
- **Tools** — CLI utilities, scripts, or helpers that extend the SDK

---

## Contribution ideas

Not sure where to start? Here are some ideas:

| Idea | Description |
|---|---|
| **Slack memory bot** | A bot that captures decisions from Slack channels and surfaces them via xysq |
| **Meeting notes agent** | Ingest meeting transcripts into the knowledge base, synthesize action items |
| **Code review assistant** | Capture code review feedback as memories, surface patterns across PRs |
| **Personal health tracker** | Capture health observations, synthesize trends over time |
| **LangChain memory backend** | Use xysq as a persistent memory backend for LangChain agents |
| **CrewAI shared memory** | Wire a CrewAI crew to share context through a team vault |
| **Custom context strategy** | Build a `ContextStrategy` that adapts retrieval based on conversation patterns |
| **CLI memory tool** | A terminal tool for quick capture/surface from the command line |

---

## Community projects

*No contributions yet — yours could be the first.*

<!-- 
Add your project here when submitting a PR:

### [Project Name](folder-name/)
**Author:** @github-username
**Description:** One-line description of what it does.
-->

---

## Guidelines

- Keep it respectful and constructive
- Don't commit API keys, tokens, or secrets
- Test your code before submitting
- Include a license in your folder if it differs from this repo's MIT license
- One project per folder, one folder per PR

---

## Questions?

- Open an issue on this repo
- Check the [SDK docs](https://docs.xysq.ai/sdk/getting-started) for API reference
- Visit [app.xysq.ai](https://app.xysq.ai/connect) to get your API key
