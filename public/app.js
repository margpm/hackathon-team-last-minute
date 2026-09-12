const form = document.querySelector('#analysis-form');
const queryInput = document.querySelector('#query');
const analyzeButton = document.querySelector('#analyze-button');
const errorMessage = document.querySelector('#error-message');
const resultStage = document.querySelector('#result-stage');
const sourceTruth = document.querySelector('#source-truth span:last-child');
const sourceNotice = document.querySelector('#source-notice');
const sourceCount = document.querySelector('#source-count');
const sourceSummary = document.querySelector('#source-summary');
const confirmedList = document.querySelector('#confirmed-list');
const conflictList = document.querySelector('#conflict-list');
const unknownList = document.querySelector('#unknown-list');
const actionTitle = document.querySelector('#action-title');
const actionReason = document.querySelector('#action-reason');
const approveButton = document.querySelector('#approve-button');
const approvalStatus = document.querySelector('#approval-status');
const sourceList = document.querySelector('#source-list');

function clearChildren(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

function appendFinding(container, title, metadata) {
  const item = document.createElement('li');
  const heading = document.createElement('span');
  const meta = document.createElement('span');

  heading.className = 'finding-title';
  heading.textContent = title;
  meta.className = 'finding-meta';
  meta.textContent = metadata;
  item.append(heading, meta);
  container.append(item);
}

function appendEmptyFinding(container, message) {
  const item = document.createElement('li');
  item.className = 'empty-finding';
  item.textContent = message;
  container.append(item);
}

function renderFindings(result) {
  clearChildren(confirmedList);
  clearChildren(conflictList);
  clearChildren(unknownList);

  for (const finding of result.confirmed) {
    appendFinding(
      confirmedList,
      finding.claim,
      finding.evidence_count + ' aligned sources: ' + finding.source_ids.join(', '),
    );
  }
  if (result.confirmed.length === 0) {
    appendEmptyFinding(confirmedList, 'No material point reached the confirmation threshold.');
  }

  for (const finding of result.conflicts) {
    appendFinding(
      conflictList,
      finding.claim,
      'For: ' + finding.supporting_source_ids.join(', ') + ' | Against: ' + finding.opposing_source_ids.join(', '),
    );
  }
  if (result.conflicts.length === 0) {
    appendEmptyFinding(conflictList, 'No materially incompatible signals found.');
  }

  for (const finding of result.unknowns) {
    appendFinding(
      unknownList,
      finding.question,
      finding.reason + ' Sources: ' + (finding.source_ids.join(', ') || 'none'),
    );
  }
  if (result.unknowns.length === 0) {
    appendEmptyFinding(unknownList, 'No unresolved material question in this context.');
  }
}

function renderSources(sources) {
  clearChildren(sourceList);
  for (const source of sources) {
    const item = document.createElement('li');
    const author = document.createElement('span');
    const text = document.createElement('strong');
    const reference = document.createElement('span');

    author.textContent = source.author;
    text.textContent = source.text;
    reference.textContent = source.id + ' | ' + new Date(source.created_at).toISOString().slice(0, 10);
    item.append(author, text, reference);
    sourceList.append(item);
  }
}

function renderResult(payload) {
  sourceTruth.textContent = payload.data_mode;
  sourceNotice.textContent = payload.source_notice;
  sourceCount.textContent = payload.sources.length + ' relevant source' + (payload.sources.length === 1 ? '' : 's');
  sourceSummary.textContent = payload.sources.length + ' local references';
  renderFindings(payload.result);
  renderSources(payload.sources);

  actionTitle.textContent = payload.result.recommended_action.title;
  actionReason.textContent = payload.result.recommended_action.reason;
  approvalStatus.textContent = 'Awaiting human approval';
  approvalStatus.classList.remove('approved');
  approveButton.disabled = false;
  resultStage.hidden = false;
}

function setLoading(isLoading) {
  analyzeButton.disabled = isLoading;
  queryInput.disabled = isLoading;
  analyzeButton.querySelector('span:first-child').textContent = isLoading ? 'Analyzing...' : 'Analyze context';
}

async function analyze() {
  const query = queryInput.value.trim();
  errorMessage.hidden = true;

  if (query.length < 3) {
    errorMessage.textContent = 'Enter a question with at least 3 characters.';
    errorMessage.hidden = false;
    queryInput.focus();
    return;
  }

  setLoading(true);
  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.message || 'Context analysis failed.');
    }

    renderResult(payload);
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
    resultStage.hidden = true;
  } finally {
    setLoading(false);
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  analyze();
});

approveButton.addEventListener('click', () => {
  approveButton.disabled = true;
  approvalStatus.textContent = 'ACTION APPROVED';
  approvalStatus.classList.add('approved');
});

analyze();
