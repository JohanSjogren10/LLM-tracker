#!/usr/bin/env python3
"""
check_models.py — LLM Tracker model checker

Fetches RSS feeds from major AI providers, detects new model announcements,
updates data/models.json, and sends an email notification.

Environment variables used:
  SMTP_SERVER    — SMTP host (e.g. smtp.gmail.com)
  SMTP_PORT      — SMTP port (default: 587)
  SMTP_USER      — sender email address
  SMTP_PASSWORD  — SMTP password or App Password
  NOTIFY_EMAIL   — recipient email address
"""

import json
import os
import re
import smtplib
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODELS_PATH = Path(__file__).parent.parent / "data" / "models.json"

RSS_SOURCES = [
    {
        "provider": "OpenAI",
        "url": "https://openai.com/blog/rss.xml",
    },
    {
        "provider": "Anthropic",
        "url": "https://www.anthropic.com/rss.xml",
    },
    {
        "provider": "Google DeepMind",
        "url": "https://deepmind.google/blog/rss.xml",
    },
    {
        "provider": "Mistral",
        "url": "https://mistral.ai/news/rss",
    },
    {
        "provider": "Meta",
        "url": "https://ai.meta.com/blog/rss/",
    },
]

# Keywords that suggest a model release announcement
RELEASE_KEYWORDS = re.compile(
    r"\b(model|release|releas|introduc|launch|announc|gpt|claude|gemini|llama|"
    r"mistral|grok|nova|o1|o3|o4|sonnet|opus|haiku|flash|pro|ultra)\b",
    re.IGNORECASE,
)

USER_AGENT = (
    "Mozilla/5.0 (compatible; LLMTracker/1.0; "
    "+https://github.com/JohanSjogren10/LLM-tracker)"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fetch_rss(url: str) -> list[dict]:
    """Fetch and parse an RSS feed, returning a list of item dicts."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=20) as resp:
            data = resp.read()
        root = ET.fromstring(data)
    except URLError as exc:
        print(f"  [WARN] Could not fetch {url}: {exc}", file=sys.stderr)
        return []
    except ET.ParseError as exc:
        print(f"  [WARN] Could not parse XML from {url}: {exc}", file=sys.stderr)
        return []

    items = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    # Handle both RSS 2.0 and Atom feeds
    for item in root.iter("item"):
        title = _text(item, "title")
        link = _text(item, "link")
        desc = _text(item, "description")
        pub_date = _parse_date(_text(item, "pubDate"))
        items.append({"title": title, "link": link, "description": desc, "date": pub_date})

    for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
        title = _text(entry, "{http://www.w3.org/2005/Atom}title")
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = link_el.get("href", "") if link_el is not None else ""
        desc = _text(entry, "{http://www.w3.org/2005/Atom}summary") or \
               _text(entry, "{http://www.w3.org/2005/Atom}content")
        pub_date = _parse_date(_text(entry, "{http://www.w3.org/2005/Atom}published") or
                               _text(entry, "{http://www.w3.org/2005/Atom}updated"))
        items.append({"title": title, "link": link, "description": desc, "date": pub_date})

    return items


def _text(el, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _parse_date(raw: str) -> str:
    """Parse various date formats to YYYY-MM-DD; fall back to today."""
    if not raw:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ):
        try:
            # Trim raw string to a reasonable max length before parsing to avoid
            # strptime errors on unexpectedly long strings. The +6 accounts for
            # optional timezone offset characters (e.g. " +0000") appended after
            # the format's own fixed-length portion.
            return datetime.strptime(raw[:len(fmt) + 6], fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Last resort: grab first 10 chars if it looks like a date
    if re.match(r"\d{4}-\d{2}-\d{2}", raw):
        return raw[:10]
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_existing_models() -> list[dict]:
    if MODELS_PATH.exists():
        with open(MODELS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_models(models: list[dict]) -> None:
    with open(MODELS_PATH, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2, ensure_ascii=False)
        f.write("\n")


def is_new_model(item: dict, existing: list[dict], provider: str) -> bool:
    """Return True if this RSS item looks like a new model release not yet tracked."""
    text = f"{item['title']} {item.get('description', '')}"
    if not RELEASE_KEYWORDS.search(text):
        return False
    title_lower = item["title"].lower()
    for m in existing:
        if m["provider"] == provider and m["model"].lower() in title_lower:
            return False
        if m.get("url") and m["url"] == item["link"]:
            return False
    return True


def extract_model_name(title: str) -> str:
    """Best-effort extraction of a model name from a blog post title."""
    # Strip common prefixes
    title = re.sub(r"^(introducing|announcing|launching|releasing|meet|welcome)\s+", "", title, flags=re.IGNORECASE)
    # Truncate at common separators
    for sep in (":", "—", " - ", " | ", " with ", " and "):
        if sep in title:
            title = title.split(sep)[0].strip()
    return title.strip() or title


def send_email(new_models: list[dict]) -> None:
    """Send an email notification for newly detected models."""
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    notify_email = os.environ.get("NOTIFY_EMAIL", "")

    if not smtp_user or not smtp_password or not notify_email:
        print("[INFO] SMTP credentials or NOTIFY_EMAIL not set — skipping email notification.", file=sys.stderr)
        return

    for model in new_models:
        subject = f"🚀 New LLM Released: {model['model']} by {model['provider']}"

        body_html = f"""\
<html>
<body style="font-family: Arial, sans-serif; background: #0d1117; color: #e6edf3; padding: 20px;">
  <h2 style="color: #58a6ff;">🚀 New LLM Detected!</h2>
  <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
    <tr>
      <td style="padding: 8px; color: #8b949e; width: 120px;"><strong>Provider</strong></td>
      <td style="padding: 8px;">{model['provider']}</td>
    </tr>
    <tr style="background: #1c2128;">
      <td style="padding: 8px; color: #8b949e;"><strong>Model</strong></td>
      <td style="padding: 8px;"><strong>{model['model']}</strong></td>
    </tr>
    <tr>
      <td style="padding: 8px; color: #8b949e;"><strong>Date</strong></td>
      <td style="padding: 8px;">{model['date']}</td>
    </tr>
    <tr style="background: #1c2128;">
      <td style="padding: 8px; color: #8b949e;"><strong>Description</strong></td>
      <td style="padding: 8px;">{model.get('description', 'N/A')}</td>
    </tr>
    <tr>
      <td style="padding: 8px; color: #8b949e;"><strong>Announcement</strong></td>
      <td style="padding: 8px;"><a href="{model['url']}" style="color: #58a6ff;">{model['url']}</a></td>
    </tr>
  </table>
  <br/>
  <p style="color: #8b949e; font-size: 12px;">
    View all models at
    <a href="https://JohanSjogren10.github.io/LLM-tracker" style="color: #58a6ff;">
      JohanSjogren10.github.io/LLM-tracker
    </a>
  </p>
</body>
</html>
"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = notify_email
        msg.attach(MIMEText(body_html, "html"))

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [notify_email], msg.as_string())
            print(f"[INFO] Email sent for {model['model']} to {notify_email}")
        except smtplib.SMTPException as exc:
            print(f"[ERROR] Failed to send email: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    existing = load_existing_models()
    existing_urls = {m.get("url") for m in existing}
    new_models: list[dict] = []

    for source in RSS_SOURCES:
        provider = source["provider"]
        print(f"[INFO] Checking {provider} ({source['url']})…")
        items = fetch_rss(source["url"])
        print(f"  Found {len(items)} RSS items")

        for item in items:
            if not is_new_model(item, existing, provider):
                continue
            model_name = extract_model_name(item["title"])
            entry = {
                "provider": provider,
                "model": model_name,
                "date": item["date"],
                "url": item["link"],
                "description": (item.get("description") or "")[:200].strip(),
            }
            # Avoid duplicates within this run
            if entry["url"] not in existing_urls:
                new_models.append(entry)
                existing_urls.add(entry["url"])
                print(f"  [NEW] {model_name} ({item['date']})")

    if new_models:
        print(f"\n[INFO] {len(new_models)} new model(s) detected. Updating models.json…")
        updated = existing + new_models
        # Sort by date descending
        updated.sort(key=lambda m: m.get("date", ""), reverse=True)
        save_models(updated)
        send_email(new_models)
        # Output JSON for workflow to consume
        print("\n=== NEW_MODELS_JSON ===")
        print(json.dumps(new_models, indent=2))
        print("=== END_NEW_MODELS_JSON ===")
    else:
        print("\n[INFO] No new models detected.")


if __name__ == "__main__":
    main()
