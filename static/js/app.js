/* Legal AI Plugin Test — Frontend Logic
   Handles: BYOK keys, document upload, parallel SSE streaming, debate rendering, export
*/

'use strict';

// ── State ─────────────────────────────────────────────────────────────────────

const state = {
  keysSet: false,
  documentLoaded: false,
  standardRunning: false,
  debateRunning: false,
  standardDone: false,
  debateDone: false,
  standardOutputText: '',   // Accumulated plain text for final review + export
  debateOutputText: '',     // Synthesis text for final review + export
  finalOutputText: '',
  tokenCounts: {
    standard: { input_tokens: 0, output_tokens: 0 },
    debate:   { input_tokens: 0, output_tokens: 0 },
    final_review: { input_tokens: 0, output_tokens: 0 },
  },
  currentPlugin: '',
  currentDocumentName: '',
};

// ── Markdown rendering ────────────────────────────────────────────────────────

marked.setOptions({ breaks: true, gfm: true });

function renderMarkdown(text) {
  if (!text) return '';
  let html = marked.parse(text);
  const wrap = document.createElement('div');
  wrap.innerHTML = html;

  wrap.querySelectorAll('pre code').forEach((codeEl, i) => {
    const pre = codeEl.parentElement;
    const wrapper = document.createElement('div');
    wrapper.className = 'code-block-wrap';
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = 'Copy';
    btn.onclick = () => copyCode(codeEl.textContent, btn);
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(btn);
    wrapper.appendChild(pre);
  });
  return wrap.innerHTML;
}

function copyCode(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
  });
}

// ── UI helpers ────────────────────────────────────────────────────────────────

function setStatus(id, msg, type = 'idle') {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.className = `status status-${type}`;
}

function toggleCard(cardId) {
  const body = document.getElementById(cardId.replace('-card', '-body'));
  const hdr  = document.querySelector(`#${cardId} .card-header`);
  if (!body || !hdr) return;
  const hidden = body.classList.toggle('hidden');
  hdr.classList.toggle('collapsed', hidden);
  hdr.querySelector('.toggle').textContent = hidden ? '▶' : '▼';
}

function showSpinner(containerId, message) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const line = document.createElement('div');
  line.className = 'loading-line';
  line.innerHTML = `<span class="spinner"></span> ${escapeHtml(message)}`;
  el.appendChild(line);
  scrollToBottom(containerId);
  return line;
}

function removeSpinner(spinnerEl) {
  if (spinnerEl && spinnerEl.parentNode) spinnerEl.parentNode.removeChild(spinnerEl);
}

function scrollToBottom(containerId) {
  const el = document.getElementById(containerId);
  if (el) el.scrollTop = el.scrollHeight;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function updateTokenPill(pillId, usage) {
  const pill = document.getElementById(pillId);
  if (!pill) return;
  const total = (usage.input_tokens || 0) + (usage.output_tokens || 0);
  if (total === 0) return;
  pill.textContent = `↑${(usage.input_tokens||0).toLocaleString()} ↓${(usage.output_tokens||0).toLocaleString()} tokens`;
  pill.style.display = 'inline-flex';
}

// ── Plugin selector ───────────────────────────────────────────────────────────

async function loadPlugins() {
  try {
    const res = await fetch('/api/plugins');
    const plugins = await res.json();
    const sel = document.getElementById('plugin-select');
    sel.innerHTML = '<option value="">— Select a plugin —</option>';
    plugins.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = `${p.icon} ${p.name}`;
      opt.title = p.description;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error('Failed to load plugins:', e);
  }
}

// ── Document upload ───────────────────────────────────────────────────────────

function handleFileUpload(input) {
  const file = input.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);

  fetch('/api/upload', { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        state.documentLoaded = true;
        state.currentDocumentName = data.filename;
        showDocInfo(`✓ Loaded: ${data.filename} (${data.char_count.toLocaleString()} chars)\n${data.preview}`);
        document.getElementById('paste-text').value = '';
      } else {
        showDocInfo(`✗ Error: ${data.error}`, true);
      }
    })
    .catch(e => showDocInfo(`✗ Upload failed: ${e.message}`, true));
}

let pasteTimer = null;
function handlePasteText() {
  clearTimeout(pasteTimer);
  pasteTimer = setTimeout(() => {
    const text = document.getElementById('paste-text').value.trim();
    if (!text) return;
    fetch('/api/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          state.documentLoaded = true;
          state.currentDocumentName = 'Pasted Text';
          showDocInfo(`✓ Pasted text loaded (${data.char_count.toLocaleString()} chars)\n${data.preview}`);
        }
      });
  }, 600);
}

function showDocInfo(msg, isError = false) {
  const el = document.getElementById('doc-info');
  el.textContent = msg;
  el.className = 'doc-info visible';
  el.style.color = isError ? '#dc2626' : '#15803d';
  el.style.background = isError ? '#fef2f2' : '#f0fdf4';
  el.style.borderColor = isError ? '#fca5a5' : '#bbf7d0';
}

// Drag and drop
const uploadZone = document.getElementById('upload-zone');
if (uploadZone) {
  uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) {
      const dt = new DataTransfer();
      dt.items.add(file);
      const input = document.getElementById('file-input');
      input.files = dt.files;
      handleFileUpload(input);
    }
  });
}

// ── API Keys ──────────────────────────────────────────────────────────────────

async function setAPIKeys() {
  const anthropicKey = document.getElementById('anthropic-key').value.trim();
  const googleKey = document.getElementById('google-key').value.trim();

  if (!anthropicKey && !googleKey) {
    document.getElementById('key-status').textContent = '✗ Please enter at least one API key';
    document.getElementById('key-status').className = 'key-status err';
    return;
  }

  try {
    const res = await fetch('/api/set-keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anthropic_key: anthropicKey, google_key: googleKey }),
    });
    const data = await res.json();
    const parts = [];
    if (data.anthropic_set) parts.push('Anthropic ✓');
    if (data.google_set) parts.push('Google ✓');
    document.getElementById('key-status').textContent = `✓ Keys set: ${parts.join(', ')}`;
    document.getElementById('key-status').className = 'key-status ok';
    state.keysSet = true;
  } catch (e) {
    document.getElementById('key-status').textContent = `✗ Error: ${e.message}`;
    document.getElementById('key-status').className = 'key-status err';
  }
}

async function checkKeys() {
  const res = await fetch('/api/check-keys');
  const data = await res.json();
  alert(`Key Status:\nAnthropic: ${data.anthropic_set ? 'Set ✓' : 'Not set'} (${data.anthropic_length} chars)\nGoogle: ${data.google_set ? 'Set ✓' : 'Not set'} (${data.google_length} chars)`);
}

// ── Validation ────────────────────────────────────────────────────────────────

function validate() {
  if (!state.keysSet) { alert('Please set your API keys first.'); return false; }
  if (!state.documentLoaded) { alert('Please upload a document or paste text first.'); return false; }
  const plugin = document.getElementById('plugin-select').value;
  if (!plugin) { alert('Please select a legal plugin.'); return false; }
  state.currentPlugin = plugin;
  return true;
}

// ── SSE streaming helper ──────────────────────────────────────────────────────

async function readSSE(url, body, onEvent) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.error || `HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // Retain incomplete line
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent(data);
        } catch (_) {}
      }
    }
  }
}

// ── Standard Analysis ─────────────────────────────────────────────────────────

async function runStandardOnly() {
  if (!validate()) return;
  setButtonsDisabled(true);
  await runStandardStream();
  setButtonsDisabled(false);
}

async function runStandardStream() {
  state.standardDone = false;
  state.standardRunning = true;
  state.standardOutputText = '';

  const model = document.getElementById('standard-model').value;
  const plugin = document.getElementById('plugin-select').value;
  const contextNotes = document.getElementById('context-notes').value;

  setStatus('std-status', `Running Standard Analysis with ${model}…`, 'loading');
  document.getElementById('std-output').innerHTML = '';

  const outputEl = document.getElementById('std-output');
  let fullText = '';

  try {
    await readSSE('/api/run-standard', {
      plugin_id: plugin,
      model,
      context_notes: contextNotes,
    }, (data) => {
      if (data.type === 'text') {
        fullText += data.text;
        outputEl.innerHTML = renderMarkdown(fullText);
        scrollToBottom('std-scroll');
      } else if (data.type === 'done') {
        state.tokenCounts.standard = data.token_counts || {};
        updateTokenPill('std-tokens', state.tokenCounts.standard);
        setStatus('std-status', '✓ Standard Analysis complete', 'success');
        state.standardOutputText = fullText;
        state.standardDone = true;
        state.standardRunning = false;
      } else if (data.type === 'error') {
        setStatus('std-status', `✗ Error: ${data.message}`, 'error');
        state.standardRunning = false;
      }
    });
  } catch (e) {
    setStatus('std-status', `✗ Error: ${e.message}`, 'error');
    state.standardRunning = false;
  }
}

// ── Debate Analysis ───────────────────────────────────────────────────────────

async function runDebateOnly() {
  if (!validate()) return;
  setButtonsDisabled(true);
  await runDebateStream();
  setButtonsDisabled(false);
}

async function runDebateStream() {
  state.debateDone = false;
  state.debateRunning = true;
  state.debateOutputText = '';

  const doerModel     = document.getElementById('doer-model').value;
  const reviewerModel = document.getElementById('reviewer-model').value;
  const plugin        = document.getElementById('plugin-select').value;
  const contextNotes  = document.getElementById('context-notes').value;
  const maxRounds     = parseInt(document.getElementById('max-rounds').value, 10);
  const exchangesPR   = parseInt(document.getElementById('exchanges-per-round').value, 10);

  setStatus('debate-status', `Running Debate (Doer: ${doerModel} / Reviewer: ${reviewerModel})…`, 'loading');
  document.getElementById('debate-output').innerHTML = '';

  const outputEl = document.getElementById('debate-output');
  let spinnerEl = null;
  let currentRound = 0;

  try {
    await readSSE('/api/run-debate', {
      plugin_id: plugin,
      doer_model: doerModel,
      reviewer_model: reviewerModel,
      max_rounds: maxRounds,
      exchanges_per_round: exchangesPR,
      context_notes: contextNotes,
    }, (data) => {

      if (data.type === 'round_start') {
        removeSpinner(spinnerEl);
        currentRound = data.round;
        const sep = document.createElement('div');
        sep.className = 'round-separator';
        sep.innerHTML = `<span>Round ${data.round} of ${data.max_rounds}</span>`;
        outputEl.appendChild(sep);
        scrollToBottom('debate-scroll');

      } else if (data.type === 'exchange_start') {
        removeSpinner(spinnerEl);
        const role = data.role === 'DOER' ? 'Doer' : 'Reviewer';
        spinnerEl = showSpinner('debate-output', `${role}: ${data.label}…`);

      } else if (data.type === 'exchange') {
        removeSpinner(spinnerEl);
        spinnerEl = null;

        const roleClass = data.role === 'DOER' ? 'ex-doer' : 'ex-reviewer';
        const roleIcon  = data.role === 'DOER' ? '🔨' : '🔍';
        const card = document.createElement('div');
        card.className = `exchange-card ${roleClass}`;
        card.innerHTML = `
          <div class="ex-head">${roleIcon} ${escapeHtml(data.label)}</div>
          <div class="ex-body md-content">${renderMarkdown(data.text)}</div>
        `;
        outputEl.appendChild(card);
        scrollToBottom('debate-scroll');

      } else if (data.type === 'consensus_check') {
        removeSpinner(spinnerEl);
        const badge = document.createElement('div');
        badge.className = `consensus-badge ${data.reached ? 'consensus-yes' : 'consensus-no'}`;
        badge.textContent = data.reached
          ? `✓ Consensus reached after Round ${data.round}: ${data.reasoning}`
          : `↻ Round ${data.round}: ${data.reasoning}`;
        outputEl.appendChild(badge);
        scrollToBottom('debate-scroll');

      } else if (data.type === 'synthesis_start') {
        removeSpinner(spinnerEl);
        const sep = document.createElement('div');
        sep.className = 'round-separator';
        sep.innerHTML = '<span>✨ Final Synthesis</span>';
        outputEl.appendChild(sep);
        spinnerEl = showSpinner('debate-output', 'Synthesizing final consensus…');

      } else if (data.type === 'synthesis') {
        removeSpinner(spinnerEl);
        spinnerEl = null;
        const card = document.createElement('div');
        card.className = 'exchange-card ex-synthesis';
        card.innerHTML = `
          <div class="ex-head">✨ Final Consensus Analysis</div>
          <div class="ex-body md-content">${renderMarkdown(data.text)}</div>
        `;
        outputEl.appendChild(card);
        state.debateOutputText = data.text;
        scrollToBottom('debate-scroll');

      } else if (data.type === 'done') {
        removeSpinner(spinnerEl);
        state.tokenCounts.debate = data.token_counts || {};
        updateTokenPill('debate-tokens', state.tokenCounts.debate);
        setStatus('debate-status', '✓ Debate complete', 'success');
        state.debateDone = true;
        state.debateRunning = false;

      } else if (data.type === 'error') {
        removeSpinner(spinnerEl);
        setStatus('debate-status', `✗ Error: ${data.message}`, 'error');
        state.debateRunning = false;
      }
    });
  } catch (e) {
    removeSpinner(spinnerEl);
    setStatus('debate-status', `✗ Error: ${e.message}`, 'error');
    state.debateRunning = false;
  }
}

// ── Run All (parallel) ────────────────────────────────────────────────────────

async function runAll() {
  if (!validate()) return;
  setButtonsDisabled(true);

  // Start both streams simultaneously
  const standardPromise = runStandardStream();
  const debatePromise   = runDebateStream();

  // Wait for both to finish
  await Promise.allSettled([standardPromise, debatePromise]);

  // Show final review panel
  document.getElementById('final-panel').style.display = 'block';
  document.getElementById('final-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  document.getElementById('export-btn').style.display = 'inline-flex';

  setButtonsDisabled(false);

  // Auto-run final review if both succeeded
  if (state.standardDone && state.debateDone) {
    setStatus('final-status', 'Both panels complete — click "Run Final Review" to compare', 'success');
    await runFinalReview();
  } else {
    setStatus('final-status', 'One or both panels encountered errors — check above', 'error');
  }
}

// ── Final Review ──────────────────────────────────────────────────────────────

async function runFinalReview() {
  if (!state.standardOutputText) {
    alert('Standard Analysis output is empty. Please run Standard Analysis first.');
    return;
  }
  if (!state.debateOutputText) {
    alert('Debate output is empty. Please run the Debate first.');
    return;
  }

  const model  = document.getElementById('final-model').value;
  const plugin = document.getElementById('plugin-select').value || state.currentPlugin;

  document.getElementById('final-panel').style.display = 'block';
  setStatus('final-status', `Running Final Review with ${model}…`, 'loading');
  document.getElementById('final-output').innerHTML = '';
  state.finalOutputText = '';

  const outputEl = document.getElementById('final-output');
  let fullText = '';

  try {
    await readSSE('/api/run-final-review', {
      plugin_id: plugin,
      model,
      standard_output: state.standardOutputText,
      debate_output: state.debateOutputText,
    }, (data) => {
      if (data.type === 'text') {
        fullText += data.text;
        outputEl.innerHTML = renderMarkdown(fullText);
        scrollToBottom('final-scroll');
      } else if (data.type === 'done') {
        state.tokenCounts.final_review = data.token_counts || {};
        updateTokenPill('final-tokens', state.tokenCounts.final_review);
        setStatus('final-status', '✓ Final Review complete', 'success');
        state.finalOutputText = fullText;
        document.getElementById('export-btn').style.display = 'inline-flex';
      } else if (data.type === 'error') {
        setStatus('final-status', `✗ Error: ${data.message}`, 'error');
      }
    });
  } catch (e) {
    setStatus('final-status', `✗ Error: ${e.message}`, 'error');
  }
}

// ── Clear All ─────────────────────────────────────────────────────────────────

function clearAll() {
  state.standardDone = false;
  state.debateDone = false;
  state.standardOutputText = '';
  state.debateOutputText = '';
  state.finalOutputText = '';
  state.tokenCounts = {
    standard: {}, debate: {}, final_review: {}
  };

  document.getElementById('std-output').innerHTML = '';
  document.getElementById('debate-output').innerHTML = '';
  document.getElementById('final-output').innerHTML = '';
  document.getElementById('final-panel').style.display = 'none';
  document.getElementById('export-btn').style.display = 'none';

  ['std-tokens', 'debate-tokens', 'final-tokens'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });

  setStatus('std-status', 'Ready — click Run to begin');
  setStatus('debate-status', 'Ready — click Run to begin');
  setStatus('final-status', 'Both panels must complete before running Final Review');
}

// ── Export ────────────────────────────────────────────────────────────────────

async function exportReport() {
  const pluginEl = document.getElementById('plugin-select');
  const pluginName = pluginEl.options[pluginEl.selectedIndex]?.text || 'Unknown Plugin';

  try {
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plugin_name: pluginName,
        document_name: state.currentDocumentName || 'Unknown',
        standard_output: state.standardOutputText,
        debate_output: state.debateOutputText,
        final_review: state.finalOutputText,
        token_counts: state.tokenCounts,
      }),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `legal-analysis-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert(`Export failed: ${e.message}`);
  }
}

// ── Button state ──────────────────────────────────────────────────────────────

function setButtonsDisabled(disabled) {
  ['run-all-btn', 'run-std-btn', 'run-debate-btn'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = disabled;
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────

window.addEventListener('DOMContentLoaded', () => {
  loadPlugins();

  // Set sensible default model selections (Sonnet for standard, Opus for reviewer)
  const modelSelects = document.querySelectorAll('select[id$="-model"]');
  const allOptions = Array.from((modelSelects[0] || { options: [] }).options).map(o => o.value);

  // Prefer claude-sonnet-4-6 as default for standard and doer
  // Prefer claude-opus-4-6 for reviewer and final-reviewer
  const sonnet = allOptions.find(v => v.includes('sonnet')) || allOptions[0];
  const opus   = allOptions.find(v => v.includes('opus'))   || allOptions[0];

  const sel = (id, val) => {
    const el = document.getElementById(id);
    if (el && val) el.value = val;
  };
  sel('standard-model', sonnet);
  sel('doer-model', sonnet);
  sel('reviewer-model', opus);
  sel('final-model', opus);
});
