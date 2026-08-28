#!/usr/bin/env python3
"""
server.py — LLM Tracker backend

A lightweight Flask server that:
  - Serves the static frontend
  - Provides user registration / login / logout
  - Lets authenticated users toggle email notifications
  - Exposes a helper to query all subscribed emails (used by check_models.py)

Database: SQLite stored in `data/llm_tracker.db`
"""

import os
import re
import secrets
import sqlite3
from pathlib import Path

import bcrypt
from flask import (
    Flask,
    g,
    jsonify,
    request,
    send_from_directory,
    session,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "llm_tracker.db"

app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """Return a per-request database connection."""
    if "db" not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


@app.teardown_appcontext
def close_db(_exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Create the users table if it doesn't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email           TEXT    NOT NULL UNIQUE,
            password_hash   TEXT    NOT NULL,
            notify_enabled  INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
MIN_PASSWORD_LEN = 8


def _validate_registration(email: str, password: str) -> str | None:
    """Return an error message or None if valid."""
    if not email or len(email) > 254 or not EMAIL_RE.match(email):
        return "A valid email address is required."
    if not password or len(password) < MIN_PASSWORD_LEN:
        return f"Password must be at least {MIN_PASSWORD_LEN} characters."
    return None


# ---------------------------------------------------------------------------
# Auth API
# ---------------------------------------------------------------------------

@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    err = _validate_registration(email, password)
    if err:
        return jsonify({"error": err}), 400

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, pw_hash),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "An account with that email already exists."}), 409

    # Auto-login after registration
    cur = db.execute("SELECT id, email, notify_enabled FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    session["user_id"] = user["id"]

    return jsonify({"id": user["id"], "email": user["email"], "notify_enabled": bool(user["notify_enabled"])}), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    db = get_db()
    cur = db.execute("SELECT id, email, password_hash, notify_enabled FROM users WHERE email = ?", (email,))
    user = cur.fetchone()

    if user is None or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Invalid email or password."}), 401

    session["user_id"] = user["id"]
    return jsonify({"id": user["id"], "email": user["email"], "notify_enabled": bool(user["notify_enabled"])})


@app.post("/api/logout")
def logout():
    session.pop("user_id", None)
    return jsonify({"ok": True})


@app.get("/api/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated."}), 401

    db = get_db()
    cur = db.execute("SELECT id, email, notify_enabled FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    if user is None:
        session.pop("user_id", None)
        return jsonify({"error": "Not authenticated."}), 401

    return jsonify({"id": user["id"], "email": user["email"], "notify_enabled": bool(user["notify_enabled"])})


@app.post("/api/notifications")
def toggle_notifications():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated."}), 401

    data = request.get_json(silent=True) or {}
    enabled = bool(data.get("enabled", True))

    db = get_db()
    db.execute("UPDATE users SET notify_enabled = ? WHERE id = ?", (int(enabled), user_id))
    db.commit()

    return jsonify({"notify_enabled": enabled})


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return send_from_directory(str(BASE_DIR), "index.html")


@app.get("/<path:filename>")
def static_files(filename: str):
    # Only serve known static file types from the project root
    safe_extensions = {".html", ".css", ".js", ".json", ".ico", ".png", ".svg", ".jpg", ".jpeg", ".webp"}
    ext = Path(filename).suffix.lower()
    if ext not in safe_extensions:
        return "Not found", 404
    full_path = BASE_DIR / filename
    if not full_path.resolve().is_relative_to(BASE_DIR):
        return "Not found", 404
    if not full_path.is_file():
        return "Not found", 404
    return send_from_directory(str(full_path.parent), full_path.name)


# ---------------------------------------------------------------------------
# Subscriber query (used by check_models.py)
# ---------------------------------------------------------------------------

def get_subscriber_emails(db_path: str | None = None) -> list[str]:
    """Return a list of emails for users who have notifications enabled."""
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    cur = conn.execute("SELECT email FROM users WHERE notify_enabled = 1")
    emails = [row[0] for row in cur.fetchall()]
    conn.close()
    return emails


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
