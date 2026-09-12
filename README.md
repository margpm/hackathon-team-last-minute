# LMCP — LastMinuteContextProof

**An agent that figures out which context actually matters before it acts.**

## The problem

AI agents today can read a huge amount of information, but they don't know what's actually important, what's outdated, what conflicts, and what's still unknown. Feeding an agent more raw context doesn't fix this — it just means the agent is confidently wrong with more data.

## What we're building

LMCP is an agent that reads difficult, noisy public context from Threads and turns it into the single best next action — instead of another summary nobody trusts.

Rather than just aggregating opinions, LMCP separates:
- **Facts** — what people actually agree on
- **Conflicts** — where opinions clearly contradict each other
- **Unknowns** — what still isn't known, based on what's been read

Then it recommends one concrete, useful action grounded in that understanding, and a human approves it before the agent acts.

## How it works

```
many Threads posts
      ↓
understand the real context
      ↓
separate facts, conflicts, and unknowns
      ↓
recommend one useful action
      ↓
human approves
      ↓
agent acts
      ↓
result is checked
```

## Example

A founder wants to know what people really think about a new AI product.

LMCP searches Threads, reads through many different opinions, and surfaces repeated problems, contradictions, and strong signals. Instead of a generic summary, it responds with:

> **This is what people agree on.**
> **This is where opinions conflict.**
> **This is what we still don't know.**
> **Based on this, here's the best next action.**

The user reviews and approves the action, and only then does the agent act.

## Why this is different

Our advantage isn't just more context — it's knowing which context matters *before* an agent acts. That's what makes the recommended action trustworthy enough to approve, instead of one more AI-generated guess.

## Data source

LMCP pulls public context from Threads via the Threads API (keyword search, and optionally publishing). See [`docs/threads_api_setup_guide.md`](docs/threads_api_setup_guide.md) for how to generate the access token and permissions needed (`threads_basic`, `threads_keyword_search`, and optionally `threads_content_publish`).

## Status

Work in progress — built during a hackathon. Architecture and stack are still being finalized.
