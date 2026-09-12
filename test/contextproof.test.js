const test = require('node:test');
const assert = require('node:assert/strict');

const { analyzeContext } = require('../src/contextproof');

function post(id, stance) {
  return {
    id,
    text: `Demo evidence ${id}`,
    author: `Demo participant ${id}`,
    url: null,
    created_at: '2026-09-12T09:00:00Z',
    topic: 'routine_setup',
    claim: 'AI voice onboarding is useful for routine setup.',
    stance,
  };
}

test('NORMAL confirms a material point only when multiple relevant posts align', () => {
  const result = analyzeContext({
    query: 'Should we use AI voice onboarding for routine setup?',
    data_mode: 'DEMO_FALLBACK_DATA',
    posts: [post('normal-1', 'support'), post('normal-2', 'support'), post('normal-3', 'support')],
  });

  assert.equal(result.confirmed.length, 1);
  assert.equal(result.confirmed[0].evidence_count, 3);
  assert.deepEqual(result.confirmed[0].source_ids, ['normal-1', 'normal-2', 'normal-3']);
  assert.equal(result.conflicts.length, 0);
  assert.equal(result.unknowns.length, 0);
  assert.equal(typeof result.recommended_action, 'object');
  assert.equal(result.source_summary.relevant_posts, 3);
});

test('CONFLICT surfaces materially incompatible signals instead of claiming consensus', () => {
  const result = analyzeContext({
    query: 'Should AI voice onboarding replace the human kickoff call?',
    data_mode: 'DEMO_FALLBACK_DATA',
    posts: [post('conflict-support', 'support'), post('conflict-oppose', 'oppose')],
  });

  assert.equal(result.confirmed.length, 0);
  assert.equal(result.conflicts.length, 1);
  assert.deepEqual(result.conflicts[0].supporting_source_ids, ['conflict-support']);
  assert.deepEqual(result.conflicts[0].opposing_source_ids, ['conflict-oppose']);
  assert.equal(result.unknowns.length, 0);
  assert.match(result.recommended_action.reason, /conflicting/i);
});

test('INSUFFICIENT returns a meaningful UNKNOWN when the context cannot establish the answer', () => {
  const result = analyzeContext({
    query: 'Will AI voice onboarding improve retention?',
    data_mode: 'DEMO_FALLBACK_DATA',
    posts: [post('insufficient-1', 'unknown')],
  });

  assert.equal(result.confirmed.length, 0);
  assert.equal(result.conflicts.length, 0);
  assert.equal(result.unknowns.length, 1);
  assert.deepEqual(result.unknowns[0].source_ids, ['insufficient-1']);
  assert.match(result.unknowns[0].reason, /does not establish/i);
  assert.match(result.recommended_action.title, /collect more direct context/i);
});
