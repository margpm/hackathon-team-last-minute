const VALID_STANCES = new Set(['support', 'oppose', 'unknown']);

function assertNonEmptyString(value, fieldName) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new TypeError(fieldName + ' must be a non-empty string.');
  }
}

function assertReferencedIds(ids, knownIds, fieldName, minimum) {
  if (!Array.isArray(ids) || ids.length < minimum) {
    throw new TypeError(fieldName + ' must contain at least ' + minimum + ' source IDs.');
  }

  const uniqueIds = new Set();
  for (const id of ids) {
    assertNonEmptyString(id, fieldName + ' source ID');
    if (!knownIds.has(id)) {
      throw new TypeError(fieldName + ' references unknown source ID: ' + id);
    }
    if (uniqueIds.has(id)) {
      throw new TypeError(fieldName + ' contains duplicate source ID: ' + id);
    }
    uniqueIds.add(id);
  }
}

function assertResultIntegrity(result, posts) {
  if (!result || typeof result !== 'object') {
    throw new TypeError('ContextProof result must be an object.');
  }

  const knownIds = new Set(posts.map((item) => item.id));
  if (!Array.isArray(result.confirmed) || !Array.isArray(result.conflicts) || !Array.isArray(result.unknowns)) {
    throw new TypeError('ContextProof result must include confirmed, conflicts, and unknowns arrays.');
  }

  for (const item of result.confirmed) {
    assertNonEmptyString(item.claim, 'Confirmed claim');
    assertReferencedIds(item.supporting_post_ids, knownIds, 'Confirmed claim', 2);
  }

  for (const item of result.conflicts) {
    assertNonEmptyString(item.topic, 'Conflict topic');
    assertNonEmptyString(item.side_a, 'Conflict side_a');
    assertNonEmptyString(item.side_b, 'Conflict side_b');
    assertReferencedIds(item.post_ids, knownIds, 'Conflict', 2);
  }

  for (const item of result.unknowns) {
    assertNonEmptyString(item.question, 'Unknown question');
    assertNonEmptyString(item.reason, 'Unknown reason');
  }

  if (!result.recommended_action || typeof result.recommended_action !== 'object') {
    throw new TypeError('ContextProof result must include exactly one recommended_action object.');
  }
  assertNonEmptyString(result.recommended_action.title, 'Recommended action title');
  assertNonEmptyString(result.recommended_action.reason, 'Recommended action reason');

  return result;
}

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

  const sourceIds = new Set();
  for (const item of input.posts) {
    if (!item || typeof item !== 'object' || typeof item.id !== 'string' || !item.id) {
      throw new TypeError('Every context post must have a non-empty id.');
    }

    if (sourceIds.has(item.id)) {
      throw new TypeError('Context post IDs must be unique: ' + item.id);
    }
    sourceIds.add(item.id);

    assertNonEmptyString(item.text, 'Context post text');
    assertNonEmptyString(item.author, 'Context post author');
    assertNonEmptyString(item.created_at, 'Context post created_at');
    if (item.url !== null && typeof item.url !== 'string') {
      throw new TypeError('Every context post url must be a string or null.');
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
    const topicKey = item.topic + '\u0000' + item.claim;
    if (!topics.has(topicKey)) {
      topics.set(topicKey, {
        claim: item.claim,
        support: [],
        oppose: [],
        unknown: [],
      });
    }

    topics.get(topicKey)[item.stance].push(item);
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
        supporting_post_ids: topic.support.map((item) => item.id),
      });
    }

    if (isConflict) {
      conflicts.push({
        topic: topic.claim,
        side_a: topic.support[0].text,
        side_b: topic.oppose[0].text,
        post_ids: [...topic.support, ...topic.oppose].map((item) => item.id),
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
  const result = {
    confirmed,
    conflicts,
    unknowns,
    recommended_action: {
      title: hasConflict
        ? `Run a bounded test: ${conflicts[0].topic}`
        : confirmed.length
          ? `Prototype: ${confirmed[0].claim}`
          : 'Collect more direct context before acting.',
      reason: hasConflict
        ? 'Relevant sources contain materially conflicting positions, so a reversible test is safer than a broad commitment.'
        : confirmed.length
          ? 'Multiple relevant sources support this bounded direction.'
          : 'The available context does not yet support a material decision.',
    },
  };

  return assertResultIntegrity(result, input.posts);
}

module.exports = {
  analyzeContext,
  assertResultIntegrity,
};
