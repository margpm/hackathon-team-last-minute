# ContextProof

**Know which context matters before an agent acts.**

ContextProof helps a builder turn public conversation into one reviewable decision: what is supported, what conflicts, what remains unknown, and the best next action to approve. Our advantage is not more context; it is knowing which context matters.

```text
Question -> relevant public signals -> SUPPORTED SIGNAL / CONFLICT / UNKNOWN
         -> exactly one best next action -> human approval -> ACTION APPROVED
```

**Try the web demo first:** `node server.js`, then open [localhost:4173](http://127.0.0.1:4173). No keys, npm install, or build required; Node.js 22+ is required. This demo uses **synthetic data and deterministic analysis**, visibly labelled in the UI. The Python live integration is implemented, but a complete live Telegram/OpenAI run has **not** been verified.

## 60-second demo

1. Open the web demo. Keep the question **"Should we build AI voice onboarding?"** and click **Analyze context**.
2. Show the three results: routine setup is supported; replacing the human kickoff is disputed; long-term retention is unknown.
3. Open **Source references** to trace each result to the seven synthetic posts.
4. Show the single proposed bounded test. Click **Approve** and show **ACTION APPROVED**.

Approval demonstrates a human decision gate. It does **not** execute the proposed test, publish a social post, or call an external action tool. Web approval is a browser-session state; Telegram approval uses an in-memory, user-bound, one-time token.

The web label `CONFIRMED` means agreement within the supplied dataset, not independently verified truth. The Python flow uses `SUPPORTED SIGNAL` to make this distinction explicit.

## What is live, and what is fallback?

Submission check: **12 September 2026**, application commit `e7616e0`.

| Component | Verified status |
| --- | --- |
| Web demo | Local question -> structured result works with `DEMO_FALLBACK_DATA` and `DETERMINISTIC_FALLBACK`. No live retrieval or model call in this mode. |
| Bluesky | Actual unauthenticated search at `api.bsky.app` returned 30 normalized posts across two queries. External availability can vary. |
| Telegram | Bot authentication succeeded. Our polling run encountered another active instance and was stopped. Complete message -> result -> approval is not verified live. |
| OpenAI | Both LLM stages are implemented through LiteLLM. A real request returned `429 credit_balance_exhausted`; successful live synthesis is not verified. |
| Threads | API/OAuth integration code is present; live retrieval is not verified. It is not required for the working web demo. |
| Deployment | Local demo verified; no public hosted demo verified in this submission check. |

Python failures remain explicit: `LIVE_SOURCE_ERROR` for retrieval failure and `MODEL_ERROR` for model or output-validation failure. Successful retrieval with no posts passes empty evidence to synthesis. The prompt requires uncertainty and never fabricated sources. The web fallback is a separate, labelled demonstration, not an automatic substitute for a failed live response.

## Architecture

```text
LIVE PYTHON PATH (anton-app-version/)
Telegram / aiogram
  -> llm_client.generate_search_queries: OpenAI call 1, 1-3 search queries
  -> bluesky_client.search_posts: sequential async retrieval, normalize, dedupe
  -> PublicContext: original question, queries, post IDs, text, authors, dates, URLs
  -> llm_client.analyze_context: OpenAI call 2, structured JSON
  -> contextproof: validate cited IDs, select evidence and one proposed action
  -> Telegram result + APPROVE -> visible approval acknowledgement
FastAPI: /health                         Audit log: data/logs/app.log

WEB FALLBACK (repository root)
Browser -> Node /api/analyze -> data/demo-fallback.json
        -> deterministic relevance/stance rules -> result -> browser approval
```

Source-ID validation rejects invented references. It does not independently prove a claim true. Context changes the recommendation: aligned signals support a prototype, conflicting signals call for a bounded test, and insufficient evidence calls for more context.

## How to run

### Web demo: no credentials

From a fresh clone, with Node.js 22+ installed:

```sh
git clone https://github.com/margpm/hackathon-team-last-minute.git
cd hackathon-team-last-minute
node server.js
```

Open [http://127.0.0.1:4173](http://127.0.0.1:4173). Leave `CONTEXT_DATA_MODE` unset, or set it to `DEMO_FALLBACK_DATA`. If port 4173 is occupied, set `PORT` to an available port before starting. This starts a local service, not a public deployment.

### Telegram + Bluesky + OpenAI

Requires Python 3.11+, an OpenAI API key with available credits, a Telegram bot token, internet access, and **only one polling instance** per bot.

From `anton-app-version/`, create a virtual environment and install `requirements.txt`. On Windows use a short checkout path such as `C:\cp` to avoid dependency-install path-length errors.

```sh
cd anton-app-version
python -m venv .venv
```

Activate with `source .venv/bin/activate` on macOS/Linux, or `.venv\Scripts\Activate.ps1` in Windows PowerShell, then:

```sh
python -m pip install -r requirements.txt
```

Create a local `.env` from [`.env.example`](anton-app-version/.env.example) only if it does not already exist. Set `BOT_TOKEN` and `OPENAI_API_KEY` privately. Keep `ACTIVE_MODEL=gpt-4o-mini` and `BLUESKY_SEARCH_URL=https://api.bsky.app/xrpc/app.bsky.feed.searchPosts`.

```sh
python -m app.main
```

Open your bot in Telegram, send `/start`, then:

> What is the biggest problem people have with AI agents today, and what should we build next?

On a successful run, inspect the evidence links and proposed action, then press **APPROVE**. [Local health](http://127.0.0.1:8000/health) reports service/configuration status; it does not prove downstream APIs are working.

## Verification and private data

Last completed automated checks: **21 Python tests and 15 Node tests passed**, plus Python compilation and dependency checks. External APIs are mocked in these suites; live observations are reported separately above.

```sh
# Repository root
node --test

# anton-app-version/, with the virtual environment active
python -m unittest discover -s tests -v
```

Python audit events include full incoming messages, model instructions, response content, and pipeline errors. Configured secrets and common token formats are redacted from these events. Logs can still contain private conversation content: keep them private. `.env`, logs, the virtual environment, runtime database, and local certificates are excluded from Git; `.env.example` contains placeholders only.

## Team and scope

Volo: PM, product, integration, demo. Mar: visual PM and UX. Anton: backend, data and retrieval. Natalia: full-stack, agent and integration.

One working decision-and-approval workflow. Not a social-listening dashboard, generic summarizer, multi-agent framework, RAG platform, or analytics suite.

[Core algorithm](docs/core_algorithm.md) | [Team brief](TEAM_BRIEF.html) (planning brief, not a live-status report)
