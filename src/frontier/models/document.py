"""Document and Page data access."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Document:
    id: int
    filename: str
    original_filename: str
    file_size: int
    page_count: int
    doc_type: str
    upload_date: str
    render_dpi: int


@dataclass
class Page:
    id: int
    document_id: int
    page_number: int
    image_path: str
    width: int | None
    height: int | None


def row_to_document(row: sqlite3.Row) -> Document:
    return Document(**dict(row))


def row_to_page(row: sqlite3.Row) -> Page:
    return Page(**dict(row))


def insert_document(
    conn: sqlite3.Connection,
    filename: str,
    original_filename: str,
    file_size: int,
    page_count: int,
    doc_type: str = "",
    render_dpi: int = 300,
) -> int:
    """Insert a document and return its ID."""
    cur = conn.execute(
        """INSERT INTO documents (filename, original_filename, file_size, page_count, doc_type, render_dpi)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (filename, original_filename, file_size, page_count, doc_type, render_dpi),
    )
    conn.commit()
    return cur.lastrowid


def list_documents(conn: sqlite3.Connection) -> list[Document]:
    """List all documents, most recent first."""
    rows = conn.execute("SELECT * FROM documents ORDER BY upload_date DESC").fetchall()
    return [row_to_document(r) for r in rows]


def get_document(conn: sqlite3.Connection, doc_id: int) -> Document | None:
    """Get a single document by ID."""
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return row_to_document(row) if row else None


def update_document(conn: sqlite3.Connection, doc_id: int, **kwargs) -> None:
    """Update document fields."""
    allowed = {"doc_type", "page_count", "filename"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [doc_id]
    conn.execute(f"UPDATE documents SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete_document(conn: sqlite3.Connection, doc_id: int) -> None:
    """Delete a document and its pages (cascade)."""
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()


def insert_page(
    conn: sqlite3.Connection,
    document_id: int,
    page_number: int,
    image_path: str,
    width: int | None = None,
    height: int | None = None,
) -> int:
    """Insert a page record and return its ID."""
    cur = conn.execute(
        """INSERT INTO pages (document_id, page_number, image_path, width, height)
           VALUES (?, ?, ?, ?, ?)""",
        (document_id, page_number, image_path, width, height),
    )
    conn.commit()
    return cur.lastrowid


def get_pages(conn: sqlite3.Connection, document_id: int) -> list[Page]:
    """Get all pages for a document, ordered by page number."""
    rows = conn.execute(
        "SELECT * FROM pages WHERE document_id = ? ORDER BY page_number",
        (document_id,),
    ).fetchall()
    return [row_to_page(r) for r in rows]


def get_document_stats(conn: sqlite3.Connection) -> dict:
    """Get aggregate stats for the dashboard."""
    row = conn.execute(
        """SELECT
            COUNT(*) as total_docs,
            COALESCE(SUM(page_count), 0) as total_pages
           FROM documents"""
    ).fetchone()
    type_rows = conn.execute(
        """SELECT doc_type, COUNT(*) as cnt
           FROM documents WHERE doc_type != '' GROUP BY doc_type"""
    ).fetchall()
    return {
        "total_docs": row["total_docs"],
        "total_pages": row["total_pages"],
        "by_type": {r["doc_type"]: r["cnt"] for r in type_rows},
    }
