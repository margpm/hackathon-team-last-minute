const test = require('node:test');
const assert = require('node:assert/strict');

const { DATA_MODES, loadContext } = require('../src/context-provider');
const { searchThreadsPosts } = require('../src/threads-adapter');

test('Threads adapter maps keyword search results to the normalized post contract', async () => {
  let observedRequest;
  const fetchImpl = async (url, options) => {
    observedRequest = { url, options };
    return {
      ok: true,
      async json() {
        return {
          data: [{
            id: 'thread-101',
            text: 'Voice onboarding made routine setup easier.',
            username: 'public_user',
            permalink: 'https://www.threads.net/@public_user/post/example',
            timestamp: '2026-09-12T10:00:00+0000',
          }],
        };
      },
    };
  };

  const context = await searchThreadsPosts('voice onboarding', {
    accessToken: 'test-token',
    fetchImpl,
  });

  const requestUrl = new URL(observedRequest.url);
  assert.equal(requestUrl.origin, 'https://graph.threads.net');
  assert.equal(requestUrl.pathname, '/keyword_search');
  assert.equal(requestUrl.searchParams.get('q'), 'voice onboarding');
  assert.equal(requestUrl.searchParams.get('search_type'), 'RECENT');
  assert.equal(observedRequest.options.headers.authorization, 'Bearer test-token');
  assert.match(context.source_notice, /live threads keyword search/i);
  assert.deepEqual(context.posts, [{
    id: 'thread-101',
    text: 'Voice onboarding made routine setup easier.',
    author: 'public_user',
    url: 'https://www.threads.net/@public_user/post/example',
    created_at: '2026-09-12T10:00:00+0000',
  }]);
});

test('Threads adapter fails explicitly when credentials are absent', async () => {
  await assert.rejects(
    () => searchThreadsPosts('voice onboarding', { accessToken: '' }),
    /THREADS_ACCESS_TOKEN is required/i,
  );
});

test('live context mode uses the Threads adapter when no custom provider is injected', async () => {
  const context = await loadContext('voice onboarding', {
    dataMode: DATA_MODES.LIVE_THREADS,
    threadsOptions: {
      accessToken: 'test-token',
      fetchImpl: async () => ({
        ok: true,
        async json() {
          return {
            data: [{
              id: 'thread-202',
              text: 'Voice onboarding was useful.',
              username: 'public_user',
              permalink: null,
              timestamp: '2026-09-12T10:00:00Z',
            }],
          };
        },
      }),
    },
  });

  assert.equal(context.data_mode, DATA_MODES.LIVE_THREADS);
  assert.equal(context.posts[0].id, 'thread-202');
  assert.match(context.source_notice, /live threads/i);
});
