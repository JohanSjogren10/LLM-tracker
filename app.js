/* app.js — LLM Tracker frontend logic */

const PROVIDER_ICONS = {
  'OpenAI': '🟢',
  'Anthropic': '🟠',
  'Google DeepMind': '🔵',
  'Meta': '🔷',
  'Mistral': '🟣',
  'xAI': '⚡',
  'Amazon': '🟡',
};

function formatDate(dateStr) {
  if (!dateStr) return 'Unknown date';
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function buildFeedItem(model) {
  const icon = PROVIDER_ICONS[model.provider] || '🤖';
  const date = formatDate(model.date);
  return `
    <div class="feed-item">
      <span class="feed-badge">${escapeHtml(icon)} ${escapeHtml(model.provider)}</span>
      <div class="feed-content">
        <div class="feed-model">
          <a href="${escapeHtml(model.url)}" target="_blank" rel="noopener">${escapeHtml(model.model)}</a>
        </div>
        <div class="feed-meta">${escapeHtml(model.description)}</div>
      </div>
      <span class="feed-date">${escapeHtml(date)}</span>
    </div>
  `;
}

function buildModelItem(model, isLatest) {
  const date = formatDate(model.date);
  return `
    <div class="model-item${isLatest ? ' latest-model' : ''}">
      <div class="model-name">
        <a href="${escapeHtml(model.url)}" target="_blank" rel="noopener">${escapeHtml(model.model)}</a>
      </div>
      <div class="model-date">${escapeHtml(date)}</div>
      <div class="model-desc">${escapeHtml(model.description)}</div>
    </div>
  `;
}

function buildProviderCard(provider, models) {
  const icon = PROVIDER_ICONS[provider] || '🤖';
  const sorted = [...models].sort((a, b) => new Date(b.date) - new Date(a.date));
  const modelItems = sorted.map((m, i) => buildModelItem(m, i === 0)).join('');
  return `
    <div class="provider-card">
      <div class="provider-header">
        <span class="provider-icon">${escapeHtml(icon)}</span>
        <span class="provider-name">${escapeHtml(provider)}</span>
      </div>
      <div class="model-list">${modelItems}</div>
    </div>
  `;
}

async function loadModels() {
  const latestFeed = document.getElementById('latest-feed');
  const providersGrid = document.getElementById('providers-grid');

  try {
    const response = await fetch('data/models.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const models = await response.json();

    // Sort all models by date descending
    models.sort((a, b) => new Date(b.date) - new Date(a.date));

    // --- Latest Feed (top 8 most recent across all providers) ---
    const latestModels = models.slice(0, 8);
    latestFeed.innerHTML = latestModels.map(buildFeedItem).join('');

    // --- Provider cards ---
    const byProvider = {};
    for (const model of models) {
      if (!byProvider[model.provider]) byProvider[model.provider] = [];
      byProvider[model.provider].push(model);
    }

    // Sort providers by their most recent model date
    const providerOrder = Object.keys(byProvider).sort((a, b) => {
      const aDate = new Date(byProvider[a][0].date);
      const bDate = new Date(byProvider[b][0].date);
      return bDate - aDate;
    });

    providersGrid.innerHTML = providerOrder.map(p => buildProviderCard(p, byProvider[p])).join('');

  } catch (err) {
    const msg = `<div class="error-msg">⚠️ Failed to load model data: ${escapeHtml(err.message)}</div>`;
    latestFeed.innerHTML = msg;
    providersGrid.innerHTML = msg;
    console.error('LLM Tracker: failed to load models.json', err);
  }
}

document.addEventListener('DOMContentLoaded', loadModels);
