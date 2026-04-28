# 🤖 LLM Tracker

A clean, dark-mode dashboard that automatically tracks the latest AI/LLM model releases from major providers and sends email notifications to all registered users when new models are detected.

**Live site:** [https://JohanSjogren10.github.io/LLM-tracker](https://JohanSjogren10.github.io/LLM-tracker)

---

## What It Does

- Displays the latest LLM releases from **OpenAI, Anthropic, Google DeepMind, Meta, Mistral, xAI (Grok), and Amazon** in a responsive dark-mode dashboard
- Shows a **"Latest Releases" feed** sorted by date across all providers
- **User accounts** — anyone can sign up with an email and password
- **Email notifications** — registered users can opt in/out of email alerts for new model releases
- Runs a **daily GitHub Actions workflow** that checks RSS feeds from each provider for new model announcements
- **Sends email notifications** to all subscribed users whenever a new model is detected
- Automatically commits updated model data back to the repository

---

## User Accounts & Notifications

The app includes a simple account system powered by **Flask + SQLite**:

1. Click **Sign up** on the site to create an account with your email and password
2. Once logged in, the **📧 Notify me** checkbox controls whether you receive email notifications
3. When the model checker detects a new release, it emails every user who has notifications enabled

Passwords are hashed with **bcrypt** and never stored in plain text.

---

## Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server (serves the frontend + API)
python server.py
```

The app runs at **http://localhost:5000** by default. Set the `PORT` environment variable to change it.

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Flask session secret key | Auto-generated |
| `PORT` | Server port | `5000` |
| `FLASK_DEBUG` | Set to `1` for debug mode | `0` |

---

## How the Notification System Works

1. The `check-models` workflow runs every day at **08:00 UTC** (and can be triggered manually)
2. `scripts/check_models.py` fetches RSS feeds from each provider and compares results to `data/models.json`
3. If a new model is detected, the script:
   - Appends the new entry to `data/models.json`
   - Commits and pushes the change (which triggers a fresh GitHub Pages deployment)
   - Reads all subscribed user emails from the SQLite database (`data/llm_tracker.db`)
   - Falls back to the `NOTIFY_EMAIL` environment variable if no database subscribers exist
   - Sends an HTML email notification to each subscriber with the model name, provider, date, description, and a link

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

The `NOTIFY_EMAIL` environment variable serves as a fallback recipient (comma-separated for multiple addresses). When users register on the site and enable notifications, their emails are read directly from the database.

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
├── app.js                      # Fetches models.json, renders UI, handles auth
├── server.py                   # Flask backend (auth, notifications, static serving)
├── requirements.txt            # Python dependencies (Flask, bcrypt)
├── data/
│   ├── models.json             # Model data (auto-updated by workflow)
│   └── llm_tracker.db          # SQLite database (auto-created, gitignored)
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

**Before the first deployment will succeed**, you must enable GitHub Pages manually:

1. Go to **Settings → Pages** in your repository
2. Under **Build and deployment → Source**, select **GitHub Actions**
3. Click **Save**
4. Push any commit to `main` (or re-run the workflow from the Actions tab) to trigger the first deployment

> **Note:** GitHub Pages is free for public repositories. For private repos, a GitHub Pro/Team/Enterprise plan is required.

---

## Running Locally

```bash
# Clone the repo
git clone https://github.com/JohanSjogren10/LLM-tracker.git
cd LLM-tracker

# Install Python dependencies
pip install -r requirements.txt

# Start the Flask server (serves frontend + API)
python server.py
```

Then open **http://localhost:5000** in your browser.

> **Note:** You can still preview just the static frontend with `python3 -m http.server 8000`, but user accounts and notifications require the Flask server.
