/* app.js — LLM Tracker frontend logic */

// ── Theme toggle ───────────────────────────────────────────────
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const icon  = document.getElementById('theme-toggle-icon');
  const label = document.getElementById('theme-toggle-label');
  if (theme === 'light') {
    icon.textContent  = '🌙';
    label.textContent = 'Dark';
  } else {
    icon.textContent  = '☀️';
    label.textContent = 'Light';
  }
}

function initTheme() {
  const saved = localStorage.getItem('llm-tracker-theme') || 'dark';
  applyTheme(saved);
  document.getElementById('theme-toggle').addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('llm-tracker-theme', next);
    applyTheme(next);
  });
}

const PROVIDER_ICONS = {
  'OpenAI': '🟢',
  'Anthropic': '🟠',
  'Google DeepMind': '🔵',
  'Meta': '🔷',
  'Mistral': '🟣',
  'xAI': '⚡',
  'DeepSeek': '🔶',
  'Amazon': '🟡',
};

function formatDate(dateStr) {
  if (!dateStr) return 'Unknown date';
  // Accept both "YYYY-MM-DD" and full ISO timestamps
  const raw = /^\d{4}-\d{2}-\d{2}$/.test(dateStr) ? dateStr + 'T00:00:00' : dateStr;
  const d = new Date(raw);
  if (isNaN(d.getTime())) return 'Unknown date';
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

// Only allow http(s) links so that a bad feed entry can't inject a
// javascript: URL into the page.
function safeUrl(url) {
  if (typeof url !== 'string') return '';
  try {
    const parsed = new URL(url, window.location.href);
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') ? parsed.href : '';
  } catch (err) {
    return '';
  }
}

// Normalise an entry from models.json so rendering never breaks on
// missing or malformed fields.
function normalizeModel(entry) {
  if (!entry || typeof entry !== 'object') return null;
  const model = typeof entry.model === 'string' ? entry.model.trim() : '';
  if (!model) return null;
  return {
    provider: (typeof entry.provider === 'string' && entry.provider.trim()) || 'Unknown',
    model,
    date: typeof entry.date === 'string' ? entry.date : '',
    url: safeUrl(entry.url),
    description: typeof entry.description === 'string' ? entry.description : '',
  };
}

function dateValue(dateStr) {
  const t = new Date(dateStr).getTime();
  return isNaN(t) ? 0 : t;
}

function buildLink(model) {
  const name = escapeHtml(model.model);
  return model.url
    ? `<a href="${escapeHtml(model.url)}" target="_blank" rel="noopener">${name}</a>`
    : name;
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
        <div class="feed-model">${buildLink(model)}</div>
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
      <div class="model-name">${buildLink(model)}</div>
      <div class="model-date">${escapeHtml(date)}</div>
      <div class="model-desc">${escapeHtml(model.description)}</div>
    </div>
  `;
}

function buildProviderCard(provider, models) {
  const icon = PROVIDER_ICONS[provider] || '🤖';
  const sorted = [...models].sort((a, b) => dateValue(b.date) - dateValue(a.date));
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

function setStatus(models) {
  const statusEl = document.getElementById('data-status');
  if (!statusEl) return;
  if (!models.length) {
    statusEl.textContent = 'No model data available yet.';
    return;
  }
  statusEl.textContent =
    `${models.length} tracked releases · most recent: ${formatDate(models[0].date)}`;
}

async function loadModels() {
  const latestFeed = document.getElementById('latest-feed');
  const providersGrid = document.getElementById('providers-grid');

  try {
    // Cache-busting: GitHub Pages (and browsers) otherwise keep serving a
    // stale models.json long after the workflow has committed new data.
    const response = await fetch(`data/models.json?t=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const raw = await response.json();
    if (!Array.isArray(raw)) throw new Error('models.json is not a list');

    const models = raw.map(normalizeModel).filter(Boolean);

    // Sort all models by date descending
    models.sort((a, b) => dateValue(b.date) - dateValue(a.date));
    setStatus(models);

    if (!models.length) {
      const empty = '<div class="loading">No model data available yet.</div>';
      latestFeed.innerHTML = empty;
      providersGrid.innerHTML = empty;
      return;
    }

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
    const providerOrder = Object.keys(byProvider).sort(
      (a, b) => dateValue(byProvider[b][0].date) - dateValue(byProvider[a][0].date)
    );

    providersGrid.innerHTML = providerOrder.map(p => buildProviderCard(p, byProvider[p])).join('');

  } catch (err) {
    const msg = `<div class="error-msg">⚠️ Failed to load model data: ${escapeHtml(err.message)}</div>`;
    latestFeed.innerHTML = msg;
    providersGrid.innerHTML = msg;
    const statusEl = document.getElementById('data-status');
    if (statusEl) statusEl.textContent = '';
    console.error('LLM Tracker: failed to load models.json', err);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadModels();
});
