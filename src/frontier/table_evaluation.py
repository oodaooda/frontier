"""Table extraction evaluation — send drawing to model, compare JSON output field-by-field."""

import json
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from frontier.database import get_db
from frontier.models.document import get_document, get_pages
from frontier.models.table_gt import get_table_gt, get_rows


@dataclass
class CellResult:
    """Result of comparing a single cell."""
    row_index: int
    column: str
    expected: str
    actual: str
    match: bool


@dataclass
class TableExtractionResult:
    """Full result of a table extraction evaluation."""
    total_cells: int
    matched_cells: int
    accuracy: float
    cell_results: list[CellResult]
    column_accuracy: dict[str, dict]  # {col: {total, matched, pct}}
    row_accuracy: list[dict]  # [{row_index, total, matched, pct}]
    model_row_count: int
    expected_row_count: int
    raw_model_output: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost: float


def build_extraction_prompt(columns: list[str], table_name: str = "") -> str:
    """Build the prompt that asks the model to extract the full table as JSON."""
    cols_str = ", ".join(f'"{c}"' for c in columns)
    return f"""You are analyzing a construction document. Extract the complete {table_name or 'table'} from this drawing as a JSON array.

Each row in the table should be a JSON object with these exact keys: [{cols_str}]

Rules:
- Extract EVERY row in the table. Do not skip any.
- Use the exact values as shown on the drawing. Do not interpret or abbreviate.
- For empty cells, use "-" or an empty string "".
- For cells marked "NOT USED" or "N.I.C.", preserve that exact text.
- Include a "level" or floor section field if rows are grouped by floor/level.
- Return ONLY the JSON array, no explanation or markdown formatting.

Respond with the JSON array only:"""


def parse_model_json(raw_output: str) -> list[dict]:
    """Extract JSON array from model output, handling markdown fences and extra text."""
    text = raw_output.strip()

    # Try to find JSON array in the output
    # Remove markdown code fences if present
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Find the JSON array
    start = text.find('[')
    end = text.rfind(']')
    if start == -1 or end == -1:
        raise ValueError("No JSON array found in model output")

    json_str = text[start:end + 1]
    return json.loads(json_str)


def normalize_value(val: str) -> str:
    """Normalize a value for comparison — case-insensitive, trimmed, consistent punctuation."""
    if val is None:
        return ""
    s = str(val).strip().lower()
    # Normalize smart quotes to ASCII
    import unicodedata
    s = s.replace(chr(0x2018), "'").replace(chr(0x2019), "'")
    s = s.replace(chr(0x02bc), "'")
    s = s.replace(chr(0x201c), '"').replace(chr(0x201d), '"')
    s = __import__('re').sub(r'\s+', ' ', s)
    return s


def compare_tables(
    expected_rows: list[dict],
    model_rows: list[dict],
    columns: list[str],
) -> TableExtractionResult:
    """Compare model output against ground truth field-by-field.

    Uses row matching by index (positional). For tables where rows may be
    reordered, a smarter matching strategy would be needed.
    """
    cell_results = []
    total = 0
    matched = 0

    # Track per-column stats
    col_stats = {c: {"total": 0, "matched": 0} for c in columns}
    row_stats = []

    max_rows = max(len(expected_rows), len(model_rows))

    for i in range(max_rows):
        exp = expected_rows[i] if i < len(expected_rows) else {}
        mod = model_rows[i] if i < len(model_rows) else {}

        row_total = 0
        row_matched = 0

        for col in columns:
            exp_val = str(exp.get(col, ""))
            mod_val = str(mod.get(col, ""))

            is_match = normalize_value(exp_val) == normalize_value(mod_val)
            total += 1
            row_total += 1

            if is_match:
                matched += 1
                row_matched += 1

            if col in col_stats:
                col_stats[col]["total"] += 1
                if is_match:
                    col_stats[col]["matched"] += 1

            cell_results.append(CellResult(
                row_index=i,
                column=col,
                expected=exp_val,
                actual=mod_val,
                match=is_match,
            ))

        row_stats.append({
            "row_index": i,
            "total": row_total,
            "matched": row_matched,
            "pct": round(row_matched / row_total * 100) if row_total > 0 else 0,
        })

    # Compute column percentages
    column_accuracy = {}
    for col, stats in col_stats.items():
        column_accuracy[col] = {
            "total": stats["total"],
            "matched": stats["matched"],
            "pct": round(stats["matched"] / stats["total"] * 100) if stats["total"] > 0 else 0,
        }

    accuracy = round(matched / total * 100, 1) if total > 0 else 0

    return TableExtractionResult(
        total_cells=total,
        matched_cells=matched,
        accuracy=accuracy,
        cell_results=cell_results,
        column_accuracy=column_accuracy,
        row_accuracy=row_stats,
        model_row_count=len(model_rows),
        expected_row_count=len(expected_rows),
        raw_model_output="",
        latency_ms=0,
        input_tokens=0,
        output_tokens=0,
        cost=0,
    )


async def run_table_extraction(
    model_db_id: int,
    document_id: int,
    table_gt_id: int,
    on_progress=None,
) -> dict:
    """Run table extraction evaluation. Returns result dict stored in DB."""
    conn = get_db()

    # Get model
    model_row = conn.execute(
        "SELECT * FROM models WHERE id = ?", (model_db_id,)
    ).fetchone()
    if not model_row:
        conn.close()
        raise ValueError(f"Model {model_db_id} not found")

    # Get document and pages
    doc = get_document(conn, document_id)
    pages = get_pages(conn, document_id)
    if not pages:
        conn.close()
        raise ValueError("No rendered pages for this document")

    # Get ground truth
    tgt = get_table_gt(conn, table_gt_id)
    gt_rows = get_rows(conn, table_gt_id)
    if not tgt or not gt_rows:
        conn.close()
        raise ValueError("No ground truth data")

    columns = tgt.columns
    expected_entries = [r.data for r in gt_rows]

    # Build prompt
    prompt = build_extraction_prompt(columns, tgt.table_name)

    # Get runner
    from frontier.evaluation import get_runner, calculate_cost
    runner = get_runner(model_row["model_id"], model_row["provider"])

    # Send all pages
    render_dir = Path("data/rendered")
    image_paths = [str(render_dir / p.image_path) for p in pages]

    if on_progress:
        on_progress("sending", 0, 0)

    start = time.monotonic()
    response = await runner.query(image_paths, prompt, f"table-extract-{table_gt_id}")
    latency_ms = (time.monotonic() - start) * 1000

    cost = calculate_cost(
        response.input_tokens, response.output_tokens,
        model_row["input_cost_per_m"], model_row["output_cost_per_m"],
    )

    if on_progress:
        on_progress("comparing", 0, 0)

    # Parse model output
    try:
        model_entries = parse_model_json(response.answer)
    except (ValueError, json.JSONDecodeError) as e:
        conn.close()
        return {
            "error": f"Failed to parse model output: {e}",
            "raw_output": response.answer[:2000],
            "latency_ms": latency_ms,
            "cost": cost,
        }

    # Compare
    result = compare_tables(expected_entries, model_entries, columns)
    result.raw_model_output = response.answer
    result.latency_ms = latency_ms
    result.input_tokens = response.input_tokens
    result.output_tokens = response.output_tokens
    result.cost = cost

    # Store result in DB
    result_data = {
        "model_id": model_row["model_id"],
        "model_name": model_row["display_name"],
        "document_id": document_id,
        "table_gt_id": table_gt_id,
        "table_name": tgt.table_name,
        "total_cells": result.total_cells,
        "matched_cells": result.matched_cells,
        "accuracy": result.accuracy,
        "model_row_count": result.model_row_count,
        "expected_row_count": result.expected_row_count,
        "column_accuracy": result.column_accuracy,
        "row_accuracy": result.row_accuracy,
        "cell_results": [
            {"row": c.row_index, "col": c.column, "expected": c.expected,
             "actual": c.actual, "match": c.match}
            for c in result.cell_results
        ],
        "latency_ms": result.latency_ms,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost": result.cost,
    }

    conn.execute(
        """INSERT INTO evaluations
           (model_id, status, total_tasks, completed_tasks, passed_tasks, total_cost, notes)
           VALUES (?, 'complete', ?, ?, ?, ?, ?)""",
        (
            model_row["model_id"],
            result.total_cells,
            result.total_cells,
            result.matched_cells,
            result.cost,
            json.dumps(result_data),
        ),
    )
    conn.commit()
    eval_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    result_data["eval_id"] = eval_id
    return result_data
