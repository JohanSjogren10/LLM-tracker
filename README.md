# 🤖 LLM Tracker

A live dashboard that tracks the latest AI language model releases from all major providers — automatically updated every day via GitHub Actions.

🌐 **Live site:** https://JohanSjogren10.github.io/LLM-tracker

---

## What it does

| Feature | Details |
|---|---|
| **Dashboard** | Dark-mode web app showing the newest LLM releases grouped by provider |
| **Providers tracked** | OpenAI, Anthropic, Google, Meta, Mistral, xAI, Cohere |
| **Auto-updates** | GitHub Actions workflow runs every day at 08:00 UTC and fetches new releases |
| **Email alerts** | Sends an email to `Johan.sjogren@tieto.com` whenever a new model is detected |
| **Hosting** | Served for free via GitHub Pages |

---

## How GitHub Pages works

GitHub Pages takes the `index.html` in the root of this repo and publishes it as a real website at:

```
https://JohanSjogren10.github.io/LLM-tracker
```

To enable it:
1. Go to **Settings → Pages** in this repo
2. Under *Source*, select **Deploy from a branch**
3. Choose **`main`** branch and **`/ (root)`** folder
4. Click **Save**

The site will be live within a minute or two.

---

## Email notification setup

Email alerts use the [`dawidd6/action-send-mail`](https://github.com/dawidd6/action-send-mail) GitHub Action via SMTP.

### Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add the following secrets:

| Secret name | Description | Example |
|---|---|---|
| `SMTP_SERVER` | Your SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port (TLS/SSL) | `465` |
| `SMTP_USERNAME` | Your email address / login | `you@gmail.com` |
| `SMTP_PASSWORD` | Your SMTP password or App Password | `••••••••` |

> **Gmail tip:** If you use Gmail, generate an [App Password](https://support.google.com/accounts/answer/185833) (requires 2-Step Verification). Use `smtp.gmail.com` as the server and port `465`.

### What the alert looks like

- **Subject:** `🚀 New LLM Model Released: Claude 4 Sonnet, GPT-5`
- **Body:** Model name, provider, release date, and link to the official announcement

---

## How to manually trigger the workflow

1. Go to the **Actions** tab in this repo
2. Select **"Fetch Latest LLM Models"** in the left sidebar
3. Click **"Run workflow"** → **"Run workflow"**

This is useful for testing or forcing an immediate update.

---

## Project structure

```
LLM-tracker/
├── index.html                        # Dark-mode dashboard (plain HTML/CSS/JS)
├── models.json                       # Model data — auto-updated by the workflow
├── _config.yml                       # GitHub Pages config
├── README.md
└── .github/
    ├── workflows/
    │   └── fetch-models.yml          # Daily scheduled workflow
    └── scripts/
        └── fetch_models.py           # Python script that fetches RSS feeds
```

---

## Tech stack

- **Frontend:** Plain HTML, CSS, JavaScript (no frameworks, no build step)
- **Data pipeline:** Python 3 + `feedparser` + `requests`
- **CI/CD:** GitHub Actions
- **Hosting:** GitHub Pages (free)
