const test = require('node:test');
const assert = require('node:assert/strict');

const { AnalysisModelError, analyzeWithOpenAI } = require('../src/openai-analyzer');

function context() {
  return {
    query: 'Should we use voice onboarding?',
    data_mode: 'LIVE_THREADS',
    posts: [
      {
        id: 'thread-1',
        text: 'Voice guidance helped me finish setup.',
        author: 'person_a',
        url: null,
        created_at: '2026-09-12T10:00:00Z',
      },
      {
        id: 'thread-2',
        text: 'Voice guidance made setup easier on mobile.',
        author: 'person_b',
        url: null,
        created_at: '2026-09-12T10:01:00Z',
      },
    ],
  };
}

function validResult() {
  return {
    confirmed: [{
      claim: 'Voice guidance can make routine setup easier.',
      supporting_post_ids: ['thread-1', 'thread-2'],
    }],
    conflicts: [],
    unknowns: [],
    recommended_action: {
      title: 'Prototype voice guidance for routine setup.',
      reason: 'Multiple retrieved posts support this bounded use case.',
    },
  };
}

test('OpenAI adapter requests strict structured output and validates source references', async () => {
  let observedRequest;
  const fetchImpl = async (url, options) => {
    observedRequest = { url, options };
    return {
      ok: true,
      async json() {
        return {
          output: [{
            type: 'message',
            content: [{ type: 'output_text', text: JSON.stringify(validResult()) }],
          }],
        };
      },
    };
  };

  const result = await analyzeWithOpenAI(context(), {
    apiKey: 'model-test-key',
    model: 'gpt-5.5',
    fetchImpl,
  });
  const requestBody = JSON.parse(observedRequest.options.body);

  assert.equal(observedRequest.url, 'https://api.openai.com/v1/responses');
  assert.equal(observedRequest.options.headers.authorization, 'Bearer model-test-key');
  assert.equal(requestBody.model, 'gpt-5.5');
  assert.equal(requestBody.store, false);
  assert.equal(requestBody.text.format.type, 'json_schema');
  assert.equal(requestBody.text.format.strict, true);
  assert.deepEqual(result, validResult());
});

test('OpenAI adapter fails closed when model output invents a source ID', async () => {
  const invalidResult = validResult();
  invalidResult.confirmed[0].supporting_post_ids[1] = 'invented-id';

  await assert.rejects(
    () => analyzeWithOpenAI(context(), {
      apiKey: 'model-test-key',
      fetchImpl: async () => ({
        ok: true,
        async json() {
          return { output_text: JSON.stringify(invalidResult) };
        },
      }),
    }),
    /unknown source id: invented-id/i,
  );
});

test('OpenAI adapter reports API failure without returning a fake result', async () => {
  await assert.rejects(
    () => analyzeWithOpenAI(context(), {
      apiKey: 'model-test-key',
      fetchImpl: async () => ({ ok: false, status: 503 }),
    }),
    (error) => error instanceof AnalysisModelError && error.code === 'OPENAI_API_ERROR',
  );
});
