# ContextProof

ContextProof turns relevant public conversation context into one evidence-bound next action with human approval.

This repository contains the first working vertical slice:

    QUESTION -> DATA -> STRUCTURED RESULT -> VISIBLE UI -> APPROVAL

## Run locally

Requirements: Node.js 20 or newer. No package install or build step is required.

    node server.js

Open http://127.0.0.1:4173.

## Test

    node --test

The test suite covers:

- NORMAL: multiple aligned sources are required before a claim is CONFIRMED.
- CONFLICT: materially incompatible positions are surfaced without false consensus.
- INSUFFICIENT: weak context returns a meaningful UNKNOWN.
- HTTP integration: query to fallback data to structured ContextProof result.

## Current data mode

The default source is explicitly labelled DEMO_FALLBACK_DATA. It contains synthetic hackathon posts with local source IDs and no invented external URLs.

src/context-provider.js is the provider boundary. It accepts either:

- DEMO_FALLBACK_DATA, available now.
- LIVE_THREADS, which fails explicitly until a live provider and valid Threads credentials are supplied.

Both modes return the same internal shape, so analysis and UI logic do not change:

    {
      query: string,
      data_mode: "LIVE_THREADS" | "DEMO_FALLBACK_DATA",
      posts: [{
        id,
        text,
        author,
        url,
        created_at,
        topic,
        claim,
        stance
      }]
    }

The output contains confirmed, conflicts, unknowns, exactly one recommended_action, and compact source counts and IDs.

## Demo questions

    Should we build AI voice onboarding?
    Should AI voice onboarding replace the human kickoff call?
    Will AI voice onboarding improve retention?

The approval button intentionally produces one deterministic local state: ACTION APPROVED.

See TEAM_BRIEF.html for the four-hour execution brief.
