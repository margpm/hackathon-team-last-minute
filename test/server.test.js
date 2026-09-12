const test = require('node:test');
const assert = require('node:assert/strict');

const { createAppServer } = require('../server');
const { AnalysisModelError } = require('../src/openai-analyzer');

test('POST /api/analyze completes the fallback query-to-structured-result path', async (t) => {
  const server = createAppServer({ dataMode: 'DEMO_FALLBACK_DATA' });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const address = server.address();
  const response = await fetch(`http://127.0.0.1:${address.port}/api/analyze`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query: 'Should we build AI voice onboarding?' }),
  });
  const payload = await response.json();

  assert.equal(response.status, 200);
  assert.equal(payload.data_mode, 'DEMO_FALLBACK_DATA');
  assert.equal(payload.analysis_mode, 'DETERMINISTIC_FALLBACK');
  assert.match(payload.source_notice, /not live threads/i);
  assert.equal(payload.result.confirmed.length, 1);
  assert.equal(payload.result.conflicts.length, 1);
  assert.equal(payload.result.unknowns.length, 1);
  assert.equal(typeof payload.result.recommended_action, 'object');
  assert.equal(Array.isArray(payload.result.recommended_action), false);
  assert.equal(payload.sources.length, 7);
  assert.deepEqual(
    payload.result.confirmed[0].supporting_post_ids,
    ['demo-routine-01', 'demo-routine-02', 'demo-routine-03'],
  );
  assert.equal(payload.sources.every((source) => source.url === null), true);
});

test('POST /api/analyze excludes tangential fallback posts from the normal path', async (t) => {
  const server = createAppServer({ dataMode: 'DEMO_FALLBACK_DATA' });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const address = server.address();
  const response = await fetch(`http://127.0.0.1:${address.port}/api/analyze`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query: 'Should we use AI voice onboarding for routine setup?' }),
  });
  const payload = await response.json();

  assert.equal(response.status, 200);
  assert.equal(payload.sources.length, 3);
  assert.equal(payload.result.confirmed.length, 1);
  assert.equal(payload.result.conflicts.length, 0);
  assert.equal(payload.result.unknowns.length, 0);
});

test('GET / visibly labels fallback mode before analysis runs', async (t) => {
  const server = createAppServer({ dataMode: 'DEMO_FALLBACK_DATA' });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const address = server.address();
  const response = await fetch(`http://127.0.0.1:${address.port}/`);
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(html, /DEMO_FALLBACK_DATA/);
});

test('model failure returns an honest error and leaves the server healthy', async (t) => {
  const server = createAppServer({
    dataMode: 'DEMO_FALLBACK_DATA',
    analyzer: async () => {
      throw new AnalysisModelError('OPENAI_API_ERROR', 'Simulated model failure.');
    },
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}`;
  const analysisResponse = await fetch(baseUrl + '/api/analyze', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query: 'Should we build AI voice onboarding?' }),
  });
  const analysisPayload = await analysisResponse.json();
  const healthResponse = await fetch(baseUrl + '/api/health');
  const healthPayload = await healthResponse.json();

  assert.equal(analysisResponse.status, 503);
  assert.equal(analysisPayload.error, 'OPENAI_API_ERROR');
  assert.equal(healthResponse.status, 200);
  assert.equal(healthPayload.status, 'ok');
});

test('live mode wires normalized Threads data into structured OpenAI analysis', async (t) => {
  const modelResult = {
    confirmed: [{
      claim: 'Voice guidance can make routine setup easier.',
      supporting_post_ids: ['live-1', 'live-2'],
    }],
    conflicts: [],
    unknowns: [],
    recommended_action: {
      title: 'Prototype voice guidance for routine setup.',
      reason: 'Multiple retrieved posts support this bounded use case.',
    },
  };
  const server = createAppServer({
    dataMode: 'LIVE_THREADS',
    threadsOptions: {
      accessToken: 'test-token',
      fetchImpl: async () => ({
        ok: true,
        async json() {
          return {
            data: [
              {
                id: 'live-1',
                text: 'Voice guidance helped me finish setup.',
                username: 'person_a',
                permalink: null,
                timestamp: '2026-09-12T10:00:00Z',
              },
              {
                id: 'live-2',
                text: 'Voice guidance made mobile setup easier.',
                username: 'person_b',
                permalink: null,
                timestamp: '2026-09-12T10:01:00Z',
              },
            ],
          };
        },
      }),
    },
    openaiOptions: {
      apiKey: 'model-test-key',
      fetchImpl: async () => ({
        ok: true,
        async json() {
          return { output_text: JSON.stringify(modelResult) };
        },
      }),
    },
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const address = server.address();
  const response = await fetch(`http://127.0.0.1:${address.port}/api/analyze`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query: 'Should we use voice guidance for setup?' }),
  });
  const payload = await response.json();

  assert.equal(response.status, 200);
  assert.equal(payload.data_mode, 'LIVE_THREADS');
  assert.equal(payload.analysis_mode, 'OPENAI_STRUCTURED');
  assert.match(payload.source_notice, /live threads keyword search/i);
  assert.deepEqual(payload.result.confirmed[0].supporting_post_ids, ['live-1', 'live-2']);
  assert.deepEqual(payload.sources.map((source) => source.id), ['live-1', 'live-2']);
});
