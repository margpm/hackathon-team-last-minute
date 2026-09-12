const DEFAULT_API_BASE = 'https://graph.threads.net';
const SEARCH_FIELDS = 'id,text,username,permalink,timestamp';

class ThreadsAdapterError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'ThreadsAdapterError';
    this.code = code;
  }
}

async function searchThreadsPosts(query, options = {}) {
  const cleanQuery = typeof query === 'string' ? query.trim() : '';
  if (!cleanQuery) {
    throw new TypeError('Threads search query is required.');
  }

  const accessToken = options.accessToken ?? process.env.THREADS_ACCESS_TOKEN;
  if (!accessToken) {
    throw new ThreadsAdapterError(
      'THREADS_CREDENTIALS_MISSING',
      'THREADS_ACCESS_TOKEN is required for live Threads search.',
    );
  }

  const fetchImpl = options.fetchImpl || fetch;
  const endpoint = new URL('/keyword_search', options.apiBase || DEFAULT_API_BASE);
  endpoint.searchParams.set('q', cleanQuery);
  endpoint.searchParams.set('search_type', 'RECENT');
  endpoint.searchParams.set('search_mode', 'KEYWORD');
  endpoint.searchParams.set('fields', SEARCH_FIELDS);
  endpoint.searchParams.set('limit', String(options.limit || 25));

  let response;
  try {
    response = await fetchImpl(endpoint.toString(), {
      method: 'GET',
      headers: {
        accept: 'application/json',
        authorization: 'Bearer ' + accessToken,
      },
      signal: options.signal || AbortSignal.timeout(options.timeoutMs || 15000),
    });
  } catch {
    throw new ThreadsAdapterError('THREADS_REQUEST_FAILED', 'Live Threads search could not be reached.');
  }

  if (!response.ok) {
    throw new ThreadsAdapterError(
      'THREADS_API_ERROR',
      'Live Threads search returned HTTP ' + response.status + '.',
    );
  }

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new ThreadsAdapterError('THREADS_INVALID_RESPONSE', 'Live Threads search returned invalid JSON.');
  }

  if (!payload || !Array.isArray(payload.data)) {
    throw new ThreadsAdapterError('THREADS_INVALID_RESPONSE', 'Live Threads search returned an invalid result shape.');
  }

  const posts = payload.data
    .filter((item) => item && typeof item.id === 'string' && typeof item.text === 'string')
    .map((item) => ({
      id: item.id,
      text: item.text,
      author: typeof item.username === 'string' && item.username ? item.username : null,
      url: typeof item.permalink === 'string' && item.permalink ? item.permalink : null,
      created_at: typeof item.timestamp === 'string' && item.timestamp ? item.timestamp : null,
    }));

  return {
    source_notice: 'Live Threads keyword search via the official API.',
    posts,
  };
}

module.exports = {
  ThreadsAdapterError,
  searchThreadsPosts,
};
