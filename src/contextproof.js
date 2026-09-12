const VALID_STANCES = new Set(['support', 'oppose', 'unknown']);

function assertContextInput(input) {
  if (!input || typeof input !== 'object') {
    throw new TypeError('Context input must be an object.');
  }

  if (typeof input.query !== 'string' || input.query.trim().length < 3) {
    throw new TypeError('Context query must contain at least 3 characters.');
  }

  if (!Array.isArray(input.posts)) {
    throw new TypeError('Context posts must be an array.');
  }

  for (const item of input.posts) {
    if (!item || typeof item !== 'object' || typeof item.id !== 'string' || !item.id) {
      throw new TypeError('Every context post must have a non-empty id.');
    }

    if (typeof item.claim !== 'string' || !item.claim || typeof item.topic !== 'string' || !item.topic) {
      throw new TypeError('Every context post must have a topic and material claim.');
    }

    if (!VALID_STANCES.has(item.stance)) {
      throw new TypeError('Every context post stance must be support, oppose, or unknown.');
    }
  }
}

function analyzeContext(input) {
  assertContextInput(input);

  const topics = new Map();
  for (const item of input.posts) {
    if (!topics.has(item.topic)) {
      topics.set(item.topic, {
        claim: item.claim,
        support: [],
        oppose: [],
        unknown: [],
      });
    }

    topics.get(item.topic)[item.stance].push(item);
  }

  const confirmed = [];
  const conflicts = [];
  const unknowns = [];
  for (const topic of topics.values()) {
    const isConfirmed = topic.support.length >= 2 && topic.oppose.length === 0;
    const isConflict = topic.support.length > 0 && topic.oppose.length > 0;

    if (isConfirmed) {
      confirmed.push({
        claim: topic.claim,
        evidence_count: topic.support.length,
        source_ids: topic.support.map((item) => item.id),
      });
    }

    if (isConflict) {
      conflicts.push({
        claim: topic.claim,
        supporting_source_ids: topic.support.map((item) => item.id),
        opposing_source_ids: topic.oppose.map((item) => item.id),
      });
    }

    if (!isConfirmed && !isConflict) {
      const sources = [...topic.support, ...topic.oppose, ...topic.unknown];
      unknowns.push({
        question: topic.claim,
        reason: sources.length === 1
          ? 'Only one relevant source addresses this point; the available context does not establish an answer.'
          : 'The available context does not establish an answer to this material point.',
        source_ids: sources.map((item) => item.id),
      });
    }
  }

  if (input.posts.length === 0) {
    unknowns.push({
      question: input.query.trim(),
      reason: 'No relevant sources were found, so the available context does not establish an answer.',
      source_ids: [],
    });
  }

  const hasConflict = conflicts.length > 0;
  return {
    confirmed,
    conflicts,
    unknowns,
    recommended_action: {
      title: hasConflict
        ? `Run a bounded test: ${conflicts[0].claim}`
        : confirmed.length
          ? `Prototype: ${confirmed[0].claim}`
          : 'Collect more direct context before acting.',
      reason: hasConflict
        ? 'Relevant sources contain materially conflicting positions, so a reversible test is safer than a broad commitment.'
        : confirmed.length
          ? 'Multiple relevant sources support this bounded direction.'
          : 'The available context does not yet support a material decision.',
    },
    source_summary: {
      mode: input.data_mode || 'UNKNOWN',
      total_posts: input.posts.length,
      relevant_posts: input.posts.length,
      source_ids: input.posts.map((item) => item.id),
    },
  };
}

module.exports = {
  analyzeContext,
};
