"""Ground truth task data access and versioning."""

import json
import sqlite3
from dataclasses import dataclass, asdict

import yaml


@dataclass
class Task:
    id: int
    document_id: int
    task_key: str
    page_number: int
    tier: int
    category: str
    question: str
    expected_answer: str
    scoring_method: str
    tolerance: float | None
    notes: str
    verified: int
    created_date: str
    updated_date: str


def row_to_task(row: sqlite3.Row) -> Task:
    return Task(**dict(row))


# ── CRUD ──────────────────────────────────────────────────────

def insert_task(
    conn: sqlite3.Connection,
    document_id: int,
    task_key: str,
    page_number: int,
    tier: int,
    category: str,
    question: str,
    expected_answer: str,
    scoring_method: str = "exact",
    tolerance: float | None = None,
    notes: str = "",
    verified: int = 0,
) -> int:
    """Insert a ground truth task and bump the GT version."""
    cur = conn.execute(
        """INSERT INTO tasks
           (document_id, task_key, page_number, tier, category, question,
            expected_answer, scoring_method, tolerance, notes, verified)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (document_id, task_key, page_number, tier, category, question,
         expected_answer, scoring_method, tolerance, notes, verified),
    )
    conn.commit()
    bump_gt_version(conn, document_id)
    return cur.lastrowid


def get_task(conn: sqlite3.Connection, task_id: int) -> Task | None:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_task(row) if row else None


def list_tasks(
    conn: sqlite3.Connection,
    document_id: int,
    page_number: int | None = None,
) -> list[Task]:
    """List tasks for a document, optionally filtered by page."""
    if page_number is not None:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE document_id = ? AND page_number = ? ORDER BY id",
            (document_id, page_number),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE document_id = ? ORDER BY page_number, id",
            (document_id,),
        ).fetchall()
    return [row_to_task(r) for r in rows]


def update_task(conn: sqlite3.Connection, task_id: int, **kwargs) -> None:
    """Update task fields and bump GT version."""
    allowed = {
        "task_key", "page_number", "tier", "category", "question",
        "expected_answer", "scoring_method", "tolerance", "notes", "verified",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    fields["updated_date"] = "datetime('now')"

    set_parts = []
    values = []
    for k, v in fields.items():
        if k == "updated_date":
            set_parts.append(f"{k} = datetime('now')")
        else:
            set_parts.append(f"{k} = ?")
            values.append(v)

    values.append(task_id)
    conn.execute(f"UPDATE tasks SET {', '.join(set_parts)} WHERE id = ?", values)
    conn.commit()

    # Get document_id to bump version
    task = get_task(conn, task_id)
    if task:
        bump_gt_version(conn, task.document_id)


def delete_task(conn: sqlite3.Connection, task_id: int) -> None:
    """Delete a task and bump GT version."""
    task = get_task(conn, task_id)
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    if task:
        bump_gt_version(conn, task.document_id)


def toggle_verified(conn: sqlite3.Connection, task_id: int) -> int:
    """Toggle verified status. Returns new status."""
    task = get_task(conn, task_id)
    if not task:
        return 0
    new_val = 0 if task.verified else 1
    conn.execute(
        "UPDATE tasks SET verified = ?, updated_date = datetime('now') WHERE id = ?",
        (new_val, task_id),
    )
    conn.commit()
    return new_val


def bulk_verify(conn: sqlite3.Connection, document_id: int, page_number: int) -> int:
    """Mark all tasks on a page as verified. Returns count updated."""
    cur = conn.execute(
        "UPDATE tasks SET verified = 1, updated_date = datetime('now') WHERE document_id = ? AND page_number = ? AND verified = 0",
        (document_id, page_number),
    )
    conn.commit()
    if cur.rowcount > 0:
        bump_gt_version(conn, document_id)
    return cur.rowcount


def get_task_stats(conn: sqlite3.Connection, document_id: int) -> dict:
    """Get task counts for a document."""
    row = conn.execute(
        """SELECT
            COUNT(*) as total,
            SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) as verified,
            SUM(CASE WHEN verified = 0 THEN 1 ELSE 0 END) as unverified
           FROM tasks WHERE document_id = ?""",
        (document_id,),
    ).fetchone()
    return {
        "total": row["total"],
        "verified": row["verified"],
        "unverified": row["unverified"],
    }


# ── Versioning ────────────────────────────────────────────────

def get_gt_version(conn: sqlite3.Connection, document_id: int) -> int:
    """Get the current GT version for a document."""
    row = conn.execute(
        "SELECT MAX(version) as v FROM gt_versions WHERE document_id = ?",
        (document_id,),
    ).fetchone()
    return row["v"] if row and row["v"] else 0


def bump_gt_version(conn: sqlite3.Connection, document_id: int) -> int:
    """Increment the GT version for a document."""
    current = get_gt_version(conn, document_id)
    new_version = current + 1
    conn.execute(
        "INSERT INTO gt_versions (document_id, version) VALUES (?, ?)",
        (document_id, new_version),
    )
    conn.commit()
    return new_version


def snapshot_gt(conn: sqlite3.Connection, document_id: int) -> int:
    """Create a frozen snapshot of the current ground truth. Returns version ID."""
    tasks = list_tasks(conn, document_id)
    snapshot_data = json.dumps([asdict(t) for t in tasks])
    current = get_gt_version(conn, document_id)
    if current == 0:
        current = bump_gt_version(conn, document_id)
    conn.execute(
        "UPDATE gt_versions SET snapshot = ? WHERE document_id = ? AND version = ?",
        (snapshot_data, document_id, current),
    )
    conn.commit()

    row = conn.execute(
        "SELECT id FROM gt_versions WHERE document_id = ? AND version = ?",
        (document_id, current),
    ).fetchone()
    return row["id"]


# ── YAML Import/Export ────────────────────────────────────────

def export_to_yaml(conn: sqlite3.Connection, document_id: int) -> str:
    """Export ground truth tasks as YAML string."""
    from frontier.models.document import get_document
    doc = get_document(conn, document_id)
    tasks = list_tasks(conn, document_id)

    data = {
        "document": doc.original_filename if doc else "unknown",
        "tasks": [],
    }
    for t in tasks:
        task_dict = {
            "id": t.task_key,
            "page": t.page_number,
            "tier": t.tier,
            "category": t.category,
            "question": t.question,
            "expected": t.expected_answer,
            "scoring": t.scoring_method,
            "verified": bool(t.verified),
        }
        if t.tolerance is not None:
            task_dict["tolerance"] = t.tolerance
        if t.notes:
            task_dict["notes"] = t.notes
        data["tasks"].append(task_dict)

    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def import_from_yaml(conn: sqlite3.Connection, document_id: int, yaml_content: str) -> int:
    """Import ground truth tasks from YAML. Returns count of tasks imported."""
    data = yaml.safe_load(yaml_content)
    if not data or "tasks" not in data:
        return 0

    count = 0
    for t in data["tasks"]:
        # Check for duplicate task_key
        existing = conn.execute(
            "SELECT id FROM tasks WHERE document_id = ? AND task_key = ?",
            (document_id, t.get("id", "")),
        ).fetchone()
        if existing:
            continue

        insert_task(
            conn,
            document_id=document_id,
            task_key=t.get("id", f"imported-{count}"),
            page_number=t.get("page", 1),
            tier=t.get("tier", 1),
            category=t.get("category", "table"),
            question=t.get("question", ""),
            expected_answer=t.get("expected", ""),
            scoring_method=t.get("scoring", "exact"),
            tolerance=t.get("tolerance"),
            notes=t.get("notes", ""),
            verified=1 if t.get("verified", False) else 0,
        )
        count += 1

    return count
