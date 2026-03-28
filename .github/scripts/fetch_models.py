#!/usr/bin/env python3
"""
fetch_models.py
───────────────
Fetches the latest LLM model releases from RSS feeds / known sources,
compares them against models.json, and appends genuinely new entries.

Outputs GitHub Actions step outputs:
  new_models  — comma-separated list of new model names (empty if none)
  email_body  — multi-line body text for the alert email
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_JSON = REPO_ROOT / "models.json"

# ─── RSS / feed sources ───────────────────────────────────────────────────────
# Each entry: (provider, feed_url, keyword_filter)
# keyword_filter: if set, only items whose title contains this string (case-insensitive) are kept
FEEDS = [
    ("OpenAI",    "https://openai.com/news/rss.xml",              r"gpt|o1|o3|o4|whisper|sora|dall-e"),
    ("Anthropic", "https://www.anthropic.com/rss.xml",            r"claude"),
    ("Google",    "https://blog.google/technology/google-deepmind/rss/", r"gemini|gemma|bard"),
    ("Meta",      "https://ai.meta.com/blog/rss/",                r"llama|meta ai"),
    ("Mistral",   "https://mistral.ai/news/rss",                  r"mistral|mixtral|codestral|mathstral"),
    ("xAI",       "https://x.ai/blog/rss.xml",                   r"grok"),
    ("Cohere",    "https://cohere.com/blog/rss",                  r"command|aya|embed"),
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_models() -> dict:
    if MODELS_JSON.exists():
        with open(MODELS_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": "", "models": []}


def save_models(data: dict) -> None:
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(MODELS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def existing_urls(data: dict) -> set:
    return {m.get("announcement_url", "") for m in data.get("models", [])}


def existing_names(data: dict) -> set:
    return {m.get("name", "").lower() for m in data.get("models", [])}


def parse_date(entry) -> str:
    """Return ISO-8601 date string from a feedparser entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d")
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:3]).strftime("%Y-%m-%d")
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def clean_text(raw: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", "", raw or "")
    return " ".join(text.split())[:200]


def slug(provider: str, title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (provider + "-" + title).lower()).strip("-")
    return base[:80]


def fetch_feed(provider: str, url: str, pattern: str) -> list[dict]:
    """Parse one RSS feed and return candidate new models."""
    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        print(f"[WARN] Failed to fetch {url}: {exc}", file=sys.stderr)
        return []

    regex = re.compile(pattern, re.IGNORECASE) if pattern else None
    results = []

    for entry in feed.entries[:20]:  # only look at 20 most-recent items
        title = getattr(entry, "title", "")
        link  = getattr(entry, "link",  "")
        summary = clean_text(getattr(entry, "summary", ""))

        if regex and not regex.search(title):
            continue

        results.append({
            "id":               slug(provider, title),
            "name":             title,
            "provider":         provider,
            "release_date":     parse_date(entry),
            "description":      summary,
            "announcement_url": link,
        })

    return results


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    data = load_models()
    seen_urls  = existing_urls(data)
    seen_names = existing_names(data)

    new_entries: list[dict] = []

    for provider, url, pattern in FEEDS:
        print(f"[INFO] Fetching {provider} feed …")
        candidates = fetch_feed(provider, url, pattern)
        for c in candidates:
            if c["announcement_url"] in seen_urls:
                continue
            if c["name"].lower() in seen_names:
                continue
            print(f"  ✚ New: {c['name']}")
            new_entries.append(c)
            seen_urls.add(c["announcement_url"])
            seen_names.add(c["name"].lower())

    if not new_entries:
        print("[INFO] No new models found.")
        set_output("new_models", "")
        set_output("email_body", "")
        return

    # Prepend newest first
    data["models"] = new_entries + data.get("models", [])
    save_models(data)
    print(f"[INFO] Added {len(new_entries)} new model(s) to models.json.")

    # Build outputs
    names_str = ", ".join(e["name"] for e in new_entries)
    body_lines = []
    for e in new_entries:
        body_lines.append(
            f"• {e['name']} ({e['provider']})\n"
            f"  Released: {e['release_date']}\n"
            f"  {e.get('description', '')}\n"
            f"  Announcement: {e.get('announcement_url', '')}\n"
        )

    set_output("new_models", names_str)
    set_output("email_body", "\n".join(body_lines))


def set_output(name: str, value: str) -> None:
    """Write a GitHub Actions step output to $GITHUB_OUTPUT."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        delimiter = "EOF_LLMTRACKER"
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
    else:
        # Running locally — just print
        print(f"OUTPUT {name}={value!r}")


if __name__ == "__main__":
    main()
