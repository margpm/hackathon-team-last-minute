# ContextProof

ContextProof turns relevant public conversation context into one evidence-bound next action with human approval.

    QUESTION -> DATA -> CONFIRMED / CONFLICT / UNKNOWN -> ONE ACTION -> APPROVAL

## Quickstart

Requirements: Node.js 22 or newer. No package install or build step is required.

    node server.js

Open http://127.0.0.1:4173.

## Architecture

- `server.js`: minimal HTTP server, static UI, health and analysis endpoints.
- `src/context-provider.js`: one normalized context boundary for live and fallback data.
- `src/threads-adapter.js`: official Threads keyword-search adapter.
- `src/openai-analyzer.js`: OpenAI Responses API with strict structured output.
- `src/contextproof.js`: deterministic fallback analyzer and source-integrity gate.
- `public/`: responsive single-screen product UI.
- `data/demo-fallback.json`: clearly labelled synthetic hackathon evidence.

Normalized posts always use this core shape:

    {
      "query": "...",
      "posts": [{
        "id": "...",
        "text": "...",
        "author": "...",
        "url": "...",
        "created_at": "..."
      }]
    }

Every CONFIRMED or CONFLICT reference is checked against the retrieved post IDs before a result is returned.

## Data modes

The zero-config default is `DEMO_FALLBACK_DATA`. It uses synthetic local posts and deterministic analysis; the UI labels both facts explicitly.

For live Threads retrieval and structured OpenAI analysis, set:

    CONTEXT_DATA_MODE=LIVE_THREADS
    THREADS_ACCESS_TOKEN=<secret>
    OPENAI_API_KEY=<secret>

Optional:

    OPENAI_MODEL=gpt-5.5

Then run `node server.js`. Live mode fails explicitly when credentials, Threads retrieval, model access, or output integrity fail. It never silently presents fallback as live.

## Test

    node --test

The suite covers:

- SUPPORT: multiple aligned posts produce CONFIRMED.
- CONFLICT: opposing material signals produce CONFLICT.
- INSUFFICIENT: weak context produces UNKNOWN.
- Source integrity: invented or duplicate references fail closed.
- Threads and OpenAI adapters through mocked network boundaries.
- Visible fallback labelling and model/API failure survival.
- HTTP query-to-result integration.

## Hackathon scope

This repository intentionally contains one local vertical slice. It does not include authentication, a database, queues, RAG, multi-agent orchestration, analytics dashboards, deployment automation, or external action execution.

`APPROVE` produces the deterministic local state `ACTION APPROVED`. See `TEAM_BRIEF.html` for team roles, timing, fallback policy, and judging alignment.
