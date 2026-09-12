# ContextProof

**An agent that knows which public context matters before it acts.**

ContextProof turns noisy public conversation into a controlled decision:

```text
Telegram question
-> live Bluesky posts
-> SUPPORTED SIGNAL / CONFLICT / UNKNOWN
-> one best next action
-> human approval
-> ACTION APPROVED
```

`SUPPORTED SIGNAL` means multiple relevant observed posts support the same point. It does not mean objective truth. Every supported signal, conflict, and evidence-backed action must reference a post ID returned by the live search.

## Primary runtime

The judge-facing application is the existing Python service in `anton-app-version/`:

- Telegram is the primary interface.
- Bluesky `app.bsky.feed.searchPosts` supplies public context without authentication.
- OpenAI structured output runs through the existing LiteLLM dependency.
- An inline `APPROVE` button produces the visible `ACTION APPROVED` state.
- FastAPI exposes `/health`; existing Threads OAuth remains available as stretch work.

Configure `anton-app-version/.env` from `.env.example`, then run:

```text
cd anton-app-version
python -m app.main
```

Required for the live flow: `BOT_TOKEN` and `OPENAI_API_KEY`. Secrets stay outside Git. Bluesky search failures return `LIVE_SOURCE_ERROR`; OpenAI failures return `MODEL_ERROR`; neither path silently substitutes fake analysis.

Run the acceptance suite from `anton-app-version/`:

```text
python -m unittest discover -s tests -v
```

## Secondary web demo

The earlier zero-build ContextProof screen remains at the repository root as a clearly labelled fallback demonstration. Run `node server.js` and open `http://127.0.0.1:4173`. It is secondary to the live Telegram flow.

See `TEAM_BRIEF.html` for the locked team scope, timeline, fallback gate, and judging alignment.
