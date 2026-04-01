"""Table ground truth data access — full table extractions with dynamic columns."""

import json
import sqlite3
from dataclasses import dataclass


@dataclass
class TableGT:
    id: int
    document_id: int
    table_name: str
    columns_json: str
    source: str
    verified: int
    created_date: str
    updated_date: str

    @property
    def columns(self) -> list[str]:
        return json.loads(self.columns_json)


@dataclass
class TableGTRow:
    id: int
    table_gt_id: int
    row_index: int
    data_json: str
    verified: int
    notes: str

    @property
    def data(self) -> dict:
        return json.loads(self.data_json)


def row_to_table_gt(row: sqlite3.Row) -> TableGT:
    return TableGT(**dict(row))


def row_to_table_gt_row(row: sqlite3.Row) -> TableGTRow:
    return TableGTRow(**dict(row))


# ── Table GT CRUD ─────────────────────────────────────────

def create_table_gt(
    conn: sqlite3.Connection,
    document_id: int,
    table_name: str,
    columns: list[str],
    source: str = "",
) -> int:
    """Create a table ground truth record. Returns its ID."""
    cur = conn.execute(
        """INSERT INTO table_ground_truth (document_id, table_name, columns_json, source)
           VALUES (?, ?, ?, ?)""",
        (document_id, table_name, json.dumps(columns), source),
    )
    conn.commit()
    return cur.lastrowid


def get_table_gt(conn: sqlite3.Connection, table_gt_id: int) -> TableGT | None:
    row = conn.execute(
        "SELECT * FROM table_ground_truth WHERE id = ?", (table_gt_id,)
    ).fetchone()
    return row_to_table_gt(row) if row else None


def list_table_gts(conn: sqlite3.Connection, document_id: int) -> list[TableGT]:
    rows = conn.execute(
        "SELECT * FROM table_ground_truth WHERE document_id = ? ORDER BY id",
        (document_id,),
    ).fetchall()
    return [row_to_table_gt(r) for r in rows]


def delete_table_gt(conn: sqlite3.Connection, table_gt_id: int) -> None:
    conn.execute("DELETE FROM table_ground_truth WHERE id = ?", (table_gt_id,))
    conn.commit()


# ── Row CRUD ──────────────────────────────────────────────

def add_row(
    conn: sqlite3.Connection,
    table_gt_id: int,
    row_index: int,
    data: dict,
) -> int:
    cur = conn.execute(
        """INSERT INTO table_gt_rows (table_gt_id, row_index, data_json)
           VALUES (?, ?, ?)""",
        (table_gt_id, row_index, json.dumps(data)),
    )
    conn.commit()
    return cur.lastrowid


def get_rows(conn: sqlite3.Connection, table_gt_id: int) -> list[TableGTRow]:
    rows = conn.execute(
        "SELECT * FROM table_gt_rows WHERE table_gt_id = ? ORDER BY row_index",
        (table_gt_id,),
    ).fetchall()
    return [row_to_table_gt_row(r) for r in rows]


def get_row(conn: sqlite3.Connection, row_id: int) -> TableGTRow | None:
    row = conn.execute(
        "SELECT * FROM table_gt_rows WHERE id = ?", (row_id,)
    ).fetchone()
    return row_to_table_gt_row(row) if row else None


def update_row_data(conn: sqlite3.Connection, row_id: int, data: dict) -> None:
    conn.execute(
        "UPDATE table_gt_rows SET data_json = ?, verified = 0 WHERE id = ?",
        (json.dumps(data), row_id),
    )
    conn.commit()


def update_cell(conn: sqlite3.Connection, row_id: int, column: str, value: str) -> None:
    """Update a single cell value in a row."""
    row = get_row(conn, row_id)
    if not row:
        return
    data = row.data
    data[column] = value
    conn.execute(
        "UPDATE table_gt_rows SET data_json = ? WHERE id = ?",
        (json.dumps(data), row_id),
    )
    conn.commit()


def toggle_row_verified(conn: sqlite3.Connection, row_id: int) -> int:
    row = get_row(conn, row_id)
    if not row:
        return 0
    new_val = 0 if row.verified else 1
    conn.execute(
        "UPDATE table_gt_rows SET verified = ? WHERE id = ?",
        (new_val, row_id),
    )
    conn.commit()
    return new_val


def get_table_gt_stats(conn: sqlite3.Connection, table_gt_id: int) -> dict:
    row = conn.execute(
        """SELECT COUNT(*) as total,
                  SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) as verified
           FROM table_gt_rows WHERE table_gt_id = ?""",
        (table_gt_id,),
    ).fetchone()
    return {"total": row["total"], "verified": row["verified"] or 0}


# ── JSON Import/Export ────────────────────────────────────

def import_json(
    conn: sqlite3.Connection,
    document_id: int,
    json_content: str,
    table_name: str = "",
    source: str = "",
) -> int:
    """Import a JSON array of objects as table ground truth. Returns table_gt_id."""
    data = json.loads(json_content)

    # Handle both flat array and structured format with _meta
    entries = []
    columns = []

    if isinstance(data, dict):
        # Structured format: {"_meta": {...}, "columns": [...], "entries": [...]}
        entries = data.get("entries", [])
        columns = data.get("columns", [])
        if not table_name and "_meta" in data:
            table_name = data["_meta"].get("sheet_title", "")
        if not source and "_meta" in data:
            source = data["_meta"].get("source", "")
    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError("JSON must be an array or object with 'entries' key")

    if not entries:
        raise ValueError("No entries found in JSON")

    # Infer columns from first entry if not specified
    if not columns:
        columns = [k for k in entries[0].keys() if not k.startswith("_")]

    table_gt_id = create_table_gt(conn, document_id, table_name, columns, source)

    for i, entry in enumerate(entries):
        # Only keep columns that are in the schema
        row_data = {k: entry.get(k, "") for k in columns}
        add_row(conn, table_gt_id, i, row_data)

    return table_gt_id


def export_json(conn: sqlite3.Connection, table_gt_id: int) -> str:
    """Export table ground truth as JSON string."""
    tgt = get_table_gt(conn, table_gt_id)
    if not tgt:
        return "[]"
    rows = get_rows(conn, table_gt_id)

    from frontier.models.document import get_document
    doc = get_document(conn, tgt.document_id)

    output = {
        "_meta": {
            "document": doc.original_filename if doc else "",
            "sheet_title": tgt.table_name,
            "source": tgt.source,
            "total_entries": len(rows),
        },
        "columns": tgt.columns,
        "entries": [r.data for r in rows],
    }
    return json.dumps(output, indent=2)
