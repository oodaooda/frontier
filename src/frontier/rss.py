"""RSS feed polling for model release news."""

import re
from datetime import datetime

import feedparser

from frontier.database import get_db

# Must match at least one phrase from REQUIRED (model-specific)
# AND at least one from CONTEXT (what happened)
REQUIRED_KEYWORDS = [
    "gpt-4", "gpt-5", "gpt-o", "o1", "o3", "o4",
    "claude", "sonnet", "opus", "haiku",
    "gemini", "llama", "mistral",
    "new model", "model release", "model update",
    "vision model", "multimodal model",
]

CONTEXT_KEYWORDS = [
    "release", "launch", "introducing", "announcing", "now available",
    "vision", "multimodal", "document understanding", "pdf",
    "benchmark", "context window", "pricing", "deprecat",
    "new capability", "api update",
]

# Exclude entries that match these patterns (noise)
EXCLUDE_KEYWORDS = [
    "chatgpt for", "safer ai", "safety bug", "teens",
    "enterprise", "partnership", "hiring", "fundrais",
    "policy", "governance", "foundation", "board",
]


def matches_keywords(text: str) -> bool:
    """Check if text matches model-related news (tight filter)."""
    lower = text.lower()
    has_required = any(kw in lower for kw in REQUIRED_KEYWORDS)
    has_context = any(kw in lower for kw in CONTEXT_KEYWORDS)
    is_excluded = any(kw in lower for kw in EXCLUDE_KEYWORDS)
    return has_required and has_context and not is_excluded


def poll_feed(feed_url: str, provider: str, feed_id: int) -> int:
    """Poll a single RSS feed and insert matching entries. Returns count of new entries."""
    feed = feedparser.parse(feed_url)
    if not feed.entries:
        return 0

    conn = get_db()
    count = 0

    for entry in feed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))
        link = entry.get("link", "")

        # Check if already exists (by headline + provider)
        existing = conn.execute(
            "SELECT id FROM news WHERE headline = ? AND provider = ?",
            (title, provider),
        ).fetchone()
        if existing:
            continue

        # Check keyword relevance
        text = f"{title} {summary}"
        if not matches_keywords(text):
            continue

        # Parse date
        published = entry.get("published", "")

        conn.execute(
            """INSERT INTO news (headline, provider, entry_type, body, source_url, status, from_rss)
               VALUES (?, ?, 'release', ?, ?, 'new', 1)""",
            (title, provider, summary[:500], link),
        )
        count += 1

    # Update last polled time
    conn.execute(
        "UPDATE rss_feeds SET last_polled = datetime('now') WHERE id = ?",
        (feed_id,),
    )
    conn.commit()
    conn.close()
    return count


def poll_all_feeds() -> dict[str, int]:
    """Poll all enabled RSS feeds. Returns {feed_name: count_new}."""
    conn = get_db()
    feeds = conn.execute(
        "SELECT * FROM rss_feeds WHERE enabled = 1"
    ).fetchall()
    conn.close()

    results = {}
    for feed in feeds:
        try:
            count = poll_feed(feed["url"], feed["provider"], feed["id"])
            results[feed["name"]] = count
        except Exception as e:
            results[feed["name"]] = f"error: {e}"

    return results
