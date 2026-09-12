# Core Processing Algorithm: Social Media RAG Pipeline

This document describes the core algorithm for the chatbot's message processing pipeline. The architecture implements a form of Retrieval-Augmented Generation (RAG) using live social media data (Bluesky / Threads) to provide contextually rich answers to user queries.

Implementers should follow this step-by-step logic when building out the message handler in `bot.py` and `llm_client.py`.

---

## Algorithm Steps

### Step 1: Ingestion
- **Action**: Receive the incoming user message from the Telegram Bot.
- **Details**: The `aiogram` message handler intercepts the user's text. A "Searching live Bluesky context..." placeholder is sent immediately to acknowledge receipt.

### Step 2: Query Generation (LLM Call 1)
- **Action**: Ask the AI model to prepare search keywords based on the user's request.
- **Details**:
  - **Prompt Construction**: Wrap the user's initial request in a system instruction designed specifically for keyword extraction.
  - *Example Prompt*: `"You are an assistant that extracts search queries. Based on the user's message: '{user_message}', generate a comma-separated list of 1-3 highly relevant keywords optimized for searching a social media platform like Bluesky or Threads. Output ONLY the keywords."*
  - **Execution**: Send this prompt to the LLM via `litellm`.

### Step 3: Social Media Retrieval
- **Action**: Parse the generated keywords and perform search queries on Bluesky and/or Threads.
- **Details**:
  - Parse the LLM's response (e.g., split by commas, clean whitespace).
  - Pass these keywords to the respective API adapters (e.g., `app/bluesky_client.py`).
  - Retrieve the top N relevant posts/threads for those keywords.

### Step 4: Context Preparation
- **Action**: Process the raw API responses and format them into a structured prompt instruction.
- **Details**:
  - Extract the text content, author, and timestamp from the retrieved posts.
  - Wrap this data into a final instruction prompt.
  - *Example Format*:
    ```text
    Please answer the user's original request using the following live context from social media:

    [Post 1]: "..."
    [Post 2]: "..."

    User's original request: {user_message}
    ```

### Step 5: Synthesis (LLM Call 2)
- **Action**: Ask the AI model to proceed with the newly constructed instruction.
- **Details**:
  - Send the heavily contextualized prompt (from Step 4) back to the LLM via `litellm`.
  - The model will read the live social media posts and synthesize an accurate, up-to-date response.

### Step 6: Delivery
- **Action**: Get the final response and send it back to the Telegram bot.
- **Details**:
  - Receive the synthesized text from the LLM.
  - Edit the original "Thinking..." placeholder message in Telegram to display the final response.
  - Handle any exceptions (e.g., API limits, network errors) by gracefully notifying the user.

---

## Architectural Notes for Implementers
* **Asynchrony**: Both LLM calls and social media API calls are I/O bound. Ensure `await` is used properly so the bot event loop is not blocked.
* **Error Handling**: If retrieval fails, return an explicit live-source error. If retrieval succeeds with no relevant posts, Step 5 proceeds with an empty evidence set and must return an honest `UNKNOWN` plus one evidence-gathering action. The model must not substitute unsupported base knowledge.
* **Modularity**: Keep the LLM calls in `llm_client.py` and the social media fetching logic in their respective clients (`bluesky_client.py`). The orchestration of these steps should occur in a dedicated pipeline function called by the `bot.py` message handler.

## Implemented Runtime Mapping

- `app/bot.py`: Telegram ingestion, immediate acknowledgement, delivery, approval, and complete incoming-message audit events.
- `app/llm_client.py`: query-generation and structured synthesis calls, including full model request instructions and response content in logs.
- `app/bluesky_client.py`: asynchronous 1-3 query retrieval, normalization, relevance filtering, and cross-query deduplication.
- `app/contextproof.py`: pipeline orchestration, source-integrity validation, key-stage events, and explicit stage errors.
- `data/logs/app.log`: UTF-8 rotating application log. Configured credentials and common token formats are redacted before writing.
