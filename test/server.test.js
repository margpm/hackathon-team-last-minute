const test = require('node:test');
const assert = require('node:assert/strict');

const { createAppServer } = require('../server');

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
  assert.match(payload.source_notice, /not live threads/i);
  assert.equal(payload.result.confirmed.length, 1);
  assert.equal(payload.result.conflicts.length, 1);
  assert.equal(payload.result.unknowns.length, 1);
  assert.equal(typeof payload.result.recommended_action, 'object');
  assert.equal(Array.isArray(payload.result.recommended_action), false);
  assert.equal(payload.sources.length, payload.result.source_summary.relevant_posts);
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
