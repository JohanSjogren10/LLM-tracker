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

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadModels();
  initAuth();
});

// ── Auth ────────────────────────────────────────────────────
let authMode = 'login'; // 'login' | 'register'

function initAuth() {
  const modal        = document.getElementById('auth-modal');
  const modalTitle   = document.getElementById('modal-title');
  const modalSwitch  = document.getElementById('modal-switch');
  const authForm     = document.getElementById('auth-form');
  const authSubmit   = document.getElementById('auth-submit');
  const authError    = document.getElementById('auth-error');
  const authEmail    = document.getElementById('auth-email');
  const authPassword = document.getElementById('auth-password');

  const loggedOut    = document.getElementById('auth-logged-out');
  const loggedIn     = document.getElementById('auth-logged-in');
  const userEmail    = document.getElementById('user-email');
  const notifyCheck  = document.getElementById('notify-checkbox');

  function showModal(mode) {
    authMode = mode;
    authError.style.display = 'none';
    authEmail.value = '';
    authPassword.value = '';
    if (mode === 'login') {
      modalTitle.textContent = 'Log in';
      authSubmit.textContent = 'Log in';
      authPassword.autocomplete = 'current-password';
      modalSwitch.innerHTML = 'Don\'t have an account? <a href="#" id="switch-to-register">Sign up</a>';
    } else {
      modalTitle.textContent = 'Create account';
      authSubmit.textContent = 'Sign up';
      authPassword.autocomplete = 'new-password';
      modalSwitch.innerHTML = 'Already have an account? <a href="#" id="switch-to-login">Log in</a>';
    }
    modal.style.display = 'flex';
    authEmail.focus();
    // Bind switch links
    const switchLink = modalSwitch.querySelector('a');
    if (switchLink) {
      switchLink.addEventListener('click', (e) => {
        e.preventDefault();
        showModal(mode === 'login' ? 'register' : 'login');
      });
    }
  }

  function hideModal() {
    modal.style.display = 'none';
  }

  function showUser(user) {
    loggedOut.style.display = 'none';
    loggedIn.style.display = 'flex';
    userEmail.textContent = user.email;
    notifyCheck.checked = user.notify_enabled;
  }

  function showLoggedOut() {
    loggedOut.style.display = 'flex';
    loggedIn.style.display = 'none';
    userEmail.textContent = '';
  }

  // Check session on load
  fetch('/api/me')
    .then(r => r.ok ? r.json() : null)
    .then(user => { if (user && user.email) showUser(user); })
    .catch(() => {});

  document.getElementById('btn-show-login').addEventListener('click', () => showModal('login'));
  document.getElementById('btn-show-register').addEventListener('click', () => showModal('register'));
  document.getElementById('modal-close').addEventListener('click', hideModal);
  modal.addEventListener('click', (e) => { if (e.target === modal) hideModal(); });

  authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    authError.style.display = 'none';
    const endpoint = authMode === 'login' ? '/api/login' : '/api/register';
    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail.value.trim(), password: authPassword.value }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        authError.textContent = data.error || 'Something went wrong.';
        authError.style.display = 'block';
        return;
      }
      hideModal();
      showUser(data);
    } catch {
      authError.textContent = 'Network error. Please try again.';
      authError.style.display = 'block';
    }
  });

  document.getElementById('btn-logout').addEventListener('click', async () => {
    await fetch('/api/logout', { method: 'POST' });
    showLoggedOut();
  });

  notifyCheck.addEventListener('change', async () => {
    try {
      await fetch('/api/notifications', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: notifyCheck.checked }),
      });
    } catch { /* ignore */ }
  });
}
