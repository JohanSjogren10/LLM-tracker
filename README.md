# 🤖 LLM Tracker

A clean, dark-mode dashboard that automatically tracks the latest AI/LLM model releases from major providers and sends email notifications when new models are detected.

**Live site:** [https://JohanSjogren10.github.io/LLM-tracker](https://JohanSjogren10.github.io/LLM-tracker)

---

## What It Does

- Displays the latest LLM releases from **OpenAI, Anthropic, Google DeepMind, Meta, Mistral, xAI (Grok), and Amazon** in a responsive dark-mode dashboard
- Shows a **"Latest Releases" feed** sorted by date across all providers
- Runs a **daily GitHub Actions workflow** that checks RSS feeds from each provider for new model announcements
- **Sends an email notification** to the configured address whenever a new model is detected
- Automatically commits updated model data back to the repository

---

## How the Notification System Works

1. The `check-models` workflow runs every day at **08:00 UTC** (and can be triggered manually)
2. `scripts/check_models.py` fetches RSS feeds from each provider and compares results to `data/models.json`
3. If a new model is detected, the script:
   - Appends the new entry to `data/models.json`
   - Commits and pushes the change (which triggers a fresh GitHub Pages deployment)
   - Sends an HTML email notification with the model name, provider, date, description, and a link

---

## Email Configuration

The notification email is sent via **SMTP (Gmail or any SMTP provider)**.

### Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions** in your repository and add:

| Secret | Description |
|---|---|
| `NOTIFICATION_EMAIL_PASSWORD` | SMTP password or [Gmail App Password](https://support.google.com/accounts/answer/185833) |
| `SMTP_USER` | The sender email address (e.g. `youremail@gmail.com`) |

> **Using Gmail?** Enable 2-Factor Authentication and generate an [App Password](https://support.google.com/accounts/answer/185833). Use that App Password as `NOTIFICATION_EMAIL_PASSWORD`.

The recipient address is hardcoded to `Johan.sjogren@tieto.com`. To change it, update `NOTIFY_EMAIL` in `.github/workflows/check-models.yml`.

---

## How to Manually Trigger a Model Check

1. Go to **Actions** tab in the repository
2. Click **"Check for New LLM Models"**
3. Click **"Run workflow"** → **"Run workflow"**

---

## Project Structure

```
LLM-tracker/
├── index.html                  # Main page
├── styles.css                  # Dark mode styles
├── app.js                      # Fetches models.json and renders the UI
├── data/
│   └── models.json             # Model data (auto-updated by workflow)
├── scripts/
│   └── check_models.py         # RSS checker & email sender
└── .github/
    └── workflows/
        ├── check-models.yml    # Daily model checker
        └── deploy.yml          # GitHub Pages deployment
```

---

## How to Add New Providers

1. **Add to the RSS sources** in `scripts/check_models.py` — add an entry to the `RSS_SOURCES` list:

```python
{
    "provider": "YourProvider",
    "url": "https://yourprovider.com/blog/rss.xml",
},
```

2. **Add an icon** in `app.js` — add to the `PROVIDER_ICONS` object:

```js
'YourProvider': '🔶',
```

3. **Pre-populate** `data/models.json` with the provider's current latest model.

---

## GitHub Pages Setup

The site is deployed automatically on every push to `main` via the `deploy.yml` workflow.

To enable GitHub Pages on a new fork:
1. Go to **Settings → Pages**
2. Set **Source** to **GitHub Actions**
3. Push any commit to `main` to trigger the first deployment
