const { assertResultIntegrity } = require('./contextproof');

const DEFAULT_MODEL = 'gpt-5.5';
const OPENAI_ENDPOINT = 'https://api.openai.com/v1/responses';

const RESULT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['confirmed', 'conflicts', 'unknowns', 'recommended_action'],
  properties: {
    confirmed: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['claim', 'supporting_post_ids'],
        properties: {
          claim: { type: 'string' },
          supporting_post_ids: {
            type: 'array',
            items: { type: 'string' },
          },
        },
      },
    },
    conflicts: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['topic', 'side_a', 'side_b', 'post_ids'],
        properties: {
          topic: { type: 'string' },
          side_a: { type: 'string' },
          side_b: { type: 'string' },
          post_ids: {
            type: 'array',
            items: { type: 'string' },
          },
        },
      },
    },
    unknowns: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['question', 'reason'],
        properties: {
          question: { type: 'string' },
          reason: { type: 'string' },
        },
      },
    },
    recommended_action: {
      type: 'object',
      additionalProperties: false,
      required: ['title', 'reason'],
      properties: {
        title: { type: 'string' },
        reason: { type: 'string' },
      },
    },
  },
};

class AnalysisModelError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'AnalysisModelError';
    this.code = code;
  }
}

function extractOutputText(payload) {
  if (typeof payload?.output_text === 'string' && payload.output_text) {
    return payload.output_text;
  }

  for (const item of payload?.output || []) {
    for (const content of item.content || []) {
      if (content.type === 'output_text' && typeof content.text === 'string') {
        return content.text;
      }
    }
  }

  return '';
}

async function analyzeWithOpenAI(context, options = {}) {
  const apiKey = options.apiKey ?? process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new AnalysisModelError('OPENAI_NOT_CONFIGURED', 'OPENAI_API_KEY is required for live model analysis.');
  }

  const fetchImpl = options.fetchImpl || fetch;
  const requestBody = {
    model: options.model || process.env.OPENAI_MODEL || DEFAULT_MODEL,
    store: false,
    instructions: [
      'Analyze only the retrieved posts supplied by the application.',
      'CONFIRMED means at least two relevant posts materially support the same claim; it is not objective truth.',
      'CONFLICT means retrieved posts materially disagree. UNKNOWN means the context does not establish an answer.',
      'Reference only supplied post IDs. Never invent facts, consensus, authors, sources, numbers, or URLs.',
      'Return exactly one bounded recommended action that requires human approval.',
    ].join(' '),
    input: JSON.stringify({
      query: context.query,
      posts: context.posts.map((item) => ({
        id: item.id,
        text: item.text,
        author: item.author,
        url: item.url,
        created_at: item.created_at,
      })),
    }),
    max_output_tokens: 1400,
    text: {
      format: {
        type: 'json_schema',
        name: 'contextproof_result',
        strict: true,
        schema: RESULT_SCHEMA,
      },
    },
  };

  let response;
  try {
    response = await fetchImpl(OPENAI_ENDPOINT, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: 'Bearer ' + apiKey,
      },
      body: JSON.stringify(requestBody),
      signal: options.signal || AbortSignal.timeout(options.timeoutMs || 30000),
    });
  } catch {
    throw new AnalysisModelError('OPENAI_REQUEST_FAILED', 'OpenAI analysis could not be reached.');
  }

  if (!response.ok) {
    throw new AnalysisModelError('OPENAI_API_ERROR', 'OpenAI analysis returned HTTP ' + response.status + '.');
  }

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new AnalysisModelError('OPENAI_INVALID_RESPONSE', 'OpenAI analysis returned invalid JSON.');
  }

  const outputText = extractOutputText(payload);
  if (!outputText) {
    throw new AnalysisModelError('OPENAI_INVALID_RESPONSE', 'OpenAI analysis returned no structured output.');
  }

  let result;
  try {
    result = JSON.parse(outputText);
    return assertResultIntegrity(result, context.posts);
  } catch (error) {
    throw new AnalysisModelError(
      'OPENAI_INVALID_OUTPUT',
      'OpenAI output failed integrity check: ' + error.message,
    );
  }
}

module.exports = {
  AnalysisModelError,
  RESULT_SCHEMA,
  analyzeWithOpenAI,
};
