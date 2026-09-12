const fs = require('node:fs');
const path = require('node:path');

const { ThreadsAdapterError, searchThreadsPosts } = require('./threads-adapter');

const DATA_MODES = Object.freeze({
  LIVE_THREADS: 'LIVE_THREADS',
  DEMO_FALLBACK_DATA: 'DEMO_FALLBACK_DATA',
});

const GENERIC_QUERY_WORDS = new Set([
  'a', 'actually', 'ai', 'an', 'and', 'are', 'based', 'build', 'do', 'for',
  'from', 'i', 'is', 'it', 'on', 'onboarding', 'people', 'saying', 'should',
  'the', 'to', 'use', 'voice', 'we', 'what', 'will', 'with',
]);

class ContextSourceError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'ContextSourceError';
    this.code = code;
  }
}

function readFallbackDataset() {
  const filePath = path.join(__dirname, '..', 'data', 'demo-fallback.json');
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function queryTokens(query) {
  return query
    .toLowerCase()
    .match(/[a-z0-9]+/g)
    ?.filter((token) => token.length > 1 && !GENERIC_QUERY_WORDS.has(token)) || [];
}

function selectRelevantPosts(query, posts) {
  const specificTokens = queryTokens(query);
  if (specificTokens.length === 0) {
    return posts;
  }

  return posts.filter((item) => {
    const searchable = (item.text + ' ' + item.claim).toLowerCase();
    return specificTokens.every((token) => searchable.includes(token));
  });
}

function normalizeContext(query, dataMode, sourceNotice, posts) {
  return {
    query: query.trim(),
    data_mode: dataMode,
    source_notice: sourceNotice,
    posts: posts.map((item) => ({
      id: item.id,
      text: item.text,
      author: item.author ?? null,
      url: item.url ?? null,
      created_at: item.created_at ?? null,
      ...(item.topic ? { topic: item.topic } : {}),
      ...(item.claim ? { claim: item.claim } : {}),
      ...(item.stance ? { stance: item.stance } : {}),
    })),
  };
}

async function loadContext(query, options = {}) {
  const cleanQuery = typeof query === 'string' ? query.trim() : '';
  if (cleanQuery.length < 3 || cleanQuery.length > 300) {
    throw new TypeError('Question must contain between 3 and 300 characters.');
  }

  const dataMode = options.dataMode || process.env.CONTEXT_DATA_MODE || DATA_MODES.DEMO_FALLBACK_DATA;

  if (dataMode === DATA_MODES.LIVE_THREADS) {
    const liveProvider = options.liveProvider || searchThreadsPosts;
    let liveContext;
    try {
      liveContext = await liveProvider(cleanQuery, options.threadsOptions || {});
    } catch (error) {
      if (error instanceof ThreadsAdapterError) {
        throw new ContextSourceError(error.code, error.message);
      }
      throw error;
    }
    if (!liveContext || !Array.isArray(liveContext.posts)) {
      throw new ContextSourceError('LIVE_THREADS_INVALID_RESPONSE', 'The live Threads provider returned invalid data.');
    }

    return normalizeContext(
      cleanQuery,
      DATA_MODES.LIVE_THREADS,
      liveContext.source_notice || 'Live Threads retrieval.',
      liveContext.posts,
    );
  }

  if (dataMode !== DATA_MODES.DEMO_FALLBACK_DATA) {
    throw new ContextSourceError('UNKNOWN_DATA_MODE', 'Unsupported context data mode: ' + dataMode);
  }

  const dataset = readFallbackDataset();
  const relevantPosts = selectRelevantPosts(cleanQuery, dataset.posts);
  return normalizeContext(cleanQuery, dataset.data_mode, dataset.source_notice, relevantPosts);
}

module.exports = {
  ContextSourceError,
  DATA_MODES,
  loadContext,
  selectRelevantPosts,
};
