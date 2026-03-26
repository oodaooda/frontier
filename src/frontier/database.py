"""SQLite database initialization and connection management."""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path("data/frontier.db")

SCHEMA = """
-- Documents: uploaded PDFs
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    page_count INTEGER NOT NULL DEFAULT 0,
    doc_type TEXT DEFAULT '',
    upload_date TEXT NOT NULL DEFAULT (datetime('now')),
    render_dpi INTEGER NOT NULL DEFAULT 300
);

-- Pages: rendered page images linked to documents
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    UNIQUE(document_id, page_number)
);

-- Ground truth tasks: Q&A pairs for evaluation
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    task_key TEXT NOT NULL,
    page_number INTEGER NOT NULL DEFAULT 1,
    tier INTEGER NOT NULL DEFAULT 1,
    category TEXT NOT NULL DEFAULT 'table',
    question TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    scoring_method TEXT NOT NULL DEFAULT 'exact',
    tolerance REAL,
    notes TEXT DEFAULT '',
    verified INTEGER NOT NULL DEFAULT 0,
    created_date TEXT NOT NULL DEFAULT (datetime('now')),
    updated_date TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Ground truth versions: track edits per document
CREATE TABLE IF NOT EXISTS gt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    created_date TEXT NOT NULL DEFAULT (datetime('now')),
    snapshot TEXT,
    UNIQUE(document_id, version)
);

-- Prompt templates
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    template TEXT NOT NULL,
    created_date TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(name, version)
);

-- Evaluation runs
CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    prompt_id INTEGER REFERENCES prompts(id),
    gt_version_id INTEGER REFERENCES gt_versions(id),
    status TEXT NOT NULL DEFAULT 'pending',
    total_tasks INTEGER NOT NULL DEFAULT 0,
    completed_tasks INTEGER NOT NULL DEFAULT 0,
    passed_tasks INTEGER NOT NULL DEFAULT 0,
    total_cost REAL NOT NULL DEFAULT 0.0,
    notes TEXT DEFAULT '',
    started_date TEXT NOT NULL DEFAULT (datetime('now')),
    completed_date TEXT
);

-- Results: per-task evaluation results
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id INTEGER NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    model_answer TEXT,
    confidence INTEGER,
    score REAL,
    passed INTEGER,
    override_passed INTEGER,
    latency_ms REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost REAL,
    raw_response TEXT,
    comment TEXT DEFAULT '',
    created_date TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Model profiles
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    display_name TEXT NOT NULL,
    release_date TEXT,
    context_window TEXT,
    max_output TEXT,
    input_cost_per_m REAL,
    output_cost_per_m REAL,
    supports_vision INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    notes TEXT DEFAULT ''
);

-- Model notes: persistent notes about model behavior
CREATE TABLE IF NOT EXISTS model_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_db_id INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    created_date TEXT NOT NULL DEFAULT (datetime('now'))
);

-- News / Model Intel entries
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    provider TEXT NOT NULL,
    entry_type TEXT NOT NULL DEFAULT 'release',
    body TEXT DEFAULT '',
    relevance TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    from_rss INTEGER NOT NULL DEFAULT 0,
    created_date TEXT NOT NULL DEFAULT (datetime('now'))
);

-- RSS feed sources
CREATE TABLE IF NOT EXISTS rss_feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_polled TEXT,
    poll_interval_hours INTEGER NOT NULL DEFAULT 6
);
"""


def get_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Get a database connection with WAL mode and foreign keys enabled."""
    path = db_path or DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Initialize the database schema."""
    conn = get_db(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def seed_defaults(db_path: Path | None = None) -> None:
    """Seed default data (prompt templates, models, RSS feeds)."""
    conn = get_db(db_path)

    # Default prompt template
    conn.execute(
        """INSERT OR IGNORE INTO prompts (name, version, template) VALUES (?, ?, ?)""",
        (
            "default",
            1,
            (
                "You are analyzing a construction document. Answer the following question "
                "based solely on what is visible in the provided image(s).\n\n"
                "Be precise and specific. If the answer involves a measurement, include the unit. "
                "If the answer involves a count, provide the exact number. "
                "If you cannot determine the answer from the image, respond with "
                '"UNABLE TO DETERMINE" and briefly explain why.\n\n'
                "Rate your confidence in your answer on a scale of 1-5:\n"
                "1 = Very uncertain, 2 = Somewhat uncertain, 3 = Moderately confident, "
                "4 = Confident, 5 = Very confident\n\n"
                "Format your response as:\n"
                "Answer: [your answer]\n"
                "Confidence: [1-5]\n\n"
                "Question: {question}"
            ),
        ),
    )

    # Default models
    for model_id, provider, display_name, input_cost, output_cost in [
        ("claude-opus-4-6", "anthropic", "Claude Opus 4.6", 5.00, 25.00),
        ("gpt-5.4", "openai", "GPT-5.4", 3.00, 15.00),
    ]:
        conn.execute(
            """INSERT OR IGNORE INTO models (model_id, provider, display_name,
               input_cost_per_m, output_cost_per_m) VALUES (?, ?, ?, ?, ?)""",
            (model_id, provider, display_name, input_cost, output_cost),
        )

    # Default RSS feeds
    for name, url, provider in [
        ("Anthropic Blog", "https://www.anthropic.com/research/rss", "anthropic"),
        ("OpenAI Blog", "https://openai.com/blog/rss.xml", "openai"),
    ]:
        conn.execute(
            """INSERT OR IGNORE INTO rss_feeds (name, url, provider) VALUES (?, ?, ?)""",
            (name, url, provider),
        )

    conn.commit()
    conn.close()
