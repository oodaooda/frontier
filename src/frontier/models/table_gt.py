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

def _flatten_structure(structure: list, columns: list[str], path: str = "") -> list[dict]:
    """Recursively flatten a hierarchical structure into flat rows.

    Handles nested headers/subheaders with activities, as found in
    construction schedules (Gantt charts, CPM bar charts).
    Each activity gets a 'header' and 'subheader' field prepended.
    """
    rows = []
    for section in structure:
        header = section.get("header", section.get("subheader", ""))
        current_path = f"{path} > {header}" if path else header

        # Collect activities at this level
        for activity in section.get("activities", []):
            row = {"header": header, "path": current_path}
            # Map activity fields to columns
            field_map = {
                "id": "Activity ID",
                "name": "Activity Name",
                "original_duration": "Original Duration",
                "remaining_duration": "Remaining Duration",
                "actual_duration": "Actual Duration",
                "early_start": "Early Start",
                "early_finish": "Early Finish",
                "late_start": "Late Start",
                "late_finish": "Late Finish",
                "total_float": "Total Float",
            }
            for key, col_name in field_map.items():
                if col_name in columns:
                    row[col_name] = str(activity.get(key, ""))
            # Also try direct column name match
            for col in columns:
                if col not in row:
                    row[col] = str(activity.get(col, ""))
            rows.append(row)

        # Recurse into subheaders
        if "subheaders" in section:
            rows.extend(_flatten_structure(section["subheaders"], columns, current_path))

    return rows


def import_json(
    conn: sqlite3.Connection,
    document_id: int,
    json_content: str,
    table_name: str = "",
    source: str = "",
) -> int:
    """Import a JSON array or structured object as table ground truth. Returns table_gt_id.

    Supports:
    - Flat array: [{"col": "val"}, ...]
    - Structured with entries: {"_meta": {...}, "columns": [...], "entries": [...]}
    - Hierarchical schedule: {"columns": [...], "structure": [{header, activities, subheaders}]}
    """
    data = json.loads(json_content)

    entries = []
    columns = []

    if isinstance(data, dict):
        # Check for hierarchical structure (construction schedules)
        if "structure" in data:
            columns = data.get("columns", [])
            # Add header/path columns for hierarchy
            if "header" not in columns:
                columns = ["header", "path"] + columns
            elif "path" not in columns:
                columns = columns[:1] + ["path"] + columns[1:]

            if not table_name and "project" in data:
                table_name = data["project"].get("title", data["project"].get("document_title", ""))
            if not source:
                source = data.get("source_file", "")

            entries = _flatten_structure(data["structure"], columns)

        # Standard structured format
        elif "entries" in data:
            entries = data["entries"]
            columns = data.get("columns", [])
            if not table_name and "_meta" in data:
                table_name = data["_meta"].get("sheet_title", "")
            if not source and "_meta" in data:
                source = data["_meta"].get("source", "")

        else:
            raise ValueError(
                "JSON object must have 'entries', 'structure', or be a flat array"
            )

    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError("JSON must be an array or object")

    if not entries:
        raise ValueError("No entries found in JSON")

    # Infer columns from first entry if not specified
    if not columns:
        columns = [k for k in entries[0].keys() if not k.startswith("_")]

    table_gt_id = create_table_gt(conn, document_id, table_name, columns, source)

    for i, entry in enumerate(entries):
        row_data = {k: str(entry.get(k, "")) for k in columns}
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
