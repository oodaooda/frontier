"""Tests for database initialization and document/page CRUD."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from frontier.database import get_db, init_db, seed_defaults
from frontier.models.document import (
    delete_document,
    get_document,
    get_document_stats,
    get_pages,
    insert_document,
    insert_page,
    list_documents,
    update_document,
)


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database."""
    path = tmp_path / "test.db"
    init_db(path)
    return path


@pytest.fixture
def conn(db_path):
    """Get a connection to the test database."""
    c = get_db(db_path)
    yield c
    c.close()


class TestDatabaseInit:
    def test_creates_tables(self, conn):
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = {r["name"] for r in tables}
        assert "documents" in table_names
        assert "pages" in table_names
        assert "tasks" in table_names
        assert "evaluations" in table_names
        assert "results" in table_names
        assert "models" in table_names
        assert "news" in table_names
        assert "prompts" in table_names
        assert "rss_feeds" in table_names

    def test_foreign_keys_enabled(self, conn):
        result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1

    def test_wal_mode(self, conn):
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0] == "wal"

    def test_seed_defaults(self, db_path):
        seed_defaults(db_path)
        conn = get_db(db_path)
        prompts = conn.execute("SELECT * FROM prompts").fetchall()
        assert len(prompts) >= 1
        assert prompts[0]["name"] == "default"

        models = conn.execute("SELECT * FROM models").fetchall()
        assert len(models) >= 2
        model_ids = {r["model_id"] for r in models}
        assert "claude-opus-4-6" in model_ids
        assert "gpt-5.4" in model_ids

        feeds = conn.execute("SELECT * FROM rss_feeds").fetchall()
        assert len(feeds) >= 2
        conn.close()

    def test_seed_idempotent(self, db_path):
        seed_defaults(db_path)
        seed_defaults(db_path)
        conn = get_db(db_path)
        models = conn.execute("SELECT * FROM models").fetchall()
        assert len(models) == 2
        conn.close()


class TestDocumentCRUD:
    def test_insert_and_get(self, conn):
        doc_id = insert_document(
            conn,
            filename="abc123.pdf",
            original_filename="A700_door_schedule.pdf",
            file_size=374000,
            page_count=1,
            doc_type="schedule",
        )
        assert doc_id is not None

        doc = get_document(conn, doc_id)
        assert doc is not None
        assert doc.filename == "abc123.pdf"
        assert doc.original_filename == "A700_door_schedule.pdf"
        assert doc.file_size == 374000
        assert doc.page_count == 1
        assert doc.doc_type == "schedule"

    def test_list_documents(self, conn):
        insert_document(conn, "a.pdf", "doc_a.pdf", 100, 1)
        insert_document(conn, "b.pdf", "doc_b.pdf", 200, 2)
        docs = list_documents(conn)
        assert len(docs) == 2
        # Both exist
        filenames = {d.filename for d in docs}
        assert filenames == {"a.pdf", "b.pdf"}

    def test_update_document(self, conn):
        doc_id = insert_document(conn, "a.pdf", "doc_a.pdf", 100, 1)
        update_document(conn, doc_id, doc_type="plan")
        doc = get_document(conn, doc_id)
        assert doc.doc_type == "plan"

    def test_update_ignores_invalid_fields(self, conn):
        doc_id = insert_document(conn, "a.pdf", "doc_a.pdf", 100, 1)
        update_document(conn, doc_id, evil_field="drop table")
        doc = get_document(conn, doc_id)
        assert doc.filename == "a.pdf"

    def test_delete_document(self, conn):
        doc_id = insert_document(conn, "a.pdf", "doc_a.pdf", 100, 1)
        insert_page(conn, doc_id, 1, "page_001.png")
        delete_document(conn, doc_id)
        assert get_document(conn, doc_id) is None
        assert get_pages(conn, doc_id) == []

    def test_get_nonexistent(self, conn):
        assert get_document(conn, 9999) is None


class TestPageCRUD:
    def test_insert_and_get_pages(self, conn):
        doc_id = insert_document(conn, "a.pdf", "a.pdf", 100, 2)
        insert_page(conn, doc_id, 1, "page_001.png", 2550, 3300)
        insert_page(conn, doc_id, 2, "page_002.png", 2550, 3300)
        pages = get_pages(conn, doc_id)
        assert len(pages) == 2
        assert pages[0].page_number == 1
        assert pages[1].page_number == 2
        assert pages[0].width == 2550

    def test_pages_ordered_by_number(self, conn):
        doc_id = insert_document(conn, "a.pdf", "a.pdf", 100, 3)
        insert_page(conn, doc_id, 3, "page_003.png")
        insert_page(conn, doc_id, 1, "page_001.png")
        insert_page(conn, doc_id, 2, "page_002.png")
        pages = get_pages(conn, doc_id)
        assert [p.page_number for p in pages] == [1, 2, 3]

    def test_cascade_delete(self, conn):
        doc_id = insert_document(conn, "a.pdf", "a.pdf", 100, 1)
        insert_page(conn, doc_id, 1, "page_001.png")
        delete_document(conn, doc_id)
        pages = get_pages(conn, doc_id)
        assert pages == []


class TestDocumentStats:
    def test_empty_stats(self, conn):
        stats = get_document_stats(conn)
        assert stats["total_docs"] == 0
        assert stats["total_pages"] == 0
        assert stats["by_type"] == {}

    def test_stats_with_data(self, conn):
        insert_document(conn, "a.pdf", "a.pdf", 100, 3, doc_type="plan")
        insert_document(conn, "b.pdf", "b.pdf", 200, 1, doc_type="schedule")
        insert_document(conn, "c.pdf", "c.pdf", 150, 2, doc_type="plan")
        stats = get_document_stats(conn)
        assert stats["total_docs"] == 3
        assert stats["total_pages"] == 6
        assert stats["by_type"]["plan"] == 2
        assert stats["by_type"]["schedule"] == 1
