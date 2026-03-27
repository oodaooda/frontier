"""RSS feed polling for model release news."""

import re
from datetime import datetime

import feedparser

from frontier.database import get_db

KEYWORDS = [
    "model", "vision", "document", "release", "api", "benchmark",
    "multimodal", "image", "pdf", "ocr", "launch", "update",
    "gpt", "claude", "gemini", "sonnet", "opus", "haiku",
]


def matches_keywords(text: str) -> bool:
    """Check if text contains any relevant keywords."""
    lower = text.lower()
    return any(kw in lower for kw in KEYWORDS)


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
