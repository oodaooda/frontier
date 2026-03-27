"""Evaluation pipeline — run ground truth tasks against a model."""

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from frontier.database import get_db
from frontier.models.document import get_document, get_pages
from frontier.models.task import list_tasks, snapshot_gt, get_gt_version
from frontier.runners.base import BaseRunner, ModelResponse


@dataclass
class ParsedAnswer:
    """Parsed model response with answer and confidence."""
    answer: str
    confidence: int | None
    raw: str


def parse_response(raw_text: str) -> ParsedAnswer:
    """Parse 'Answer: ...' and 'Confidence: ...' from model response."""
    answer = raw_text.strip()
    confidence = None

    # Try to extract Answer: line
    answer_match = re.search(r"Answer:\s*(.+?)(?:\n|$)", raw_text, re.IGNORECASE)
    if answer_match:
        answer = answer_match.group(1).strip()

    # Try to extract Confidence: line
    conf_match = re.search(r"Confidence:\s*(\d)", raw_text, re.IGNORECASE)
    if conf_match:
        confidence = int(conf_match.group(1))

    return ParsedAnswer(answer=answer, confidence=confidence, raw=raw_text)


def get_runner(model_id: str, provider: str) -> BaseRunner:
    """Get a runner instance for the given model."""
    if provider == "anthropic":
        from frontier.runners.anthropic_runner import AnthropicRunner
        return AnthropicRunner(model_id=model_id)
    elif provider == "openai":
        from frontier.runners.openai_runner import OpenAIRunner
        return OpenAIRunner(model_id=model_id)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    input_cost_per_m: float,
    output_cost_per_m: float,
) -> float:
    """Calculate cost in dollars."""
    return (input_tokens * input_cost_per_m / 1_000_000) + (
        output_tokens * output_cost_per_m / 1_000_000
    )


async def run_evaluation(
    model_db_id: int,
    document_ids: list[int],
    prompt_id: int | None = None,
    verified_only: bool = True,
    notes: str = "",
    on_progress=None,
    eval_id: int | None = None,
) -> int:
    """Run evaluation and return evaluation ID.

    Args:
        model_db_id: Database ID of the model to use.
        document_ids: List of document IDs to evaluate.
        prompt_id: Prompt template ID (uses default if None).
        verified_only: Only evaluate verified tasks.
        notes: Run notes.
        on_progress: Callback(completed, total, passed, cost) for progress updates.
        eval_id: Existing evaluation record ID (if created by caller).

    Returns:
        Evaluation ID.
    """
    conn = get_db()

    # Get model info
    model_row = conn.execute(
        "SELECT * FROM models WHERE id = ?", (model_db_id,)
    ).fetchone()
    if not model_row:
        conn.close()
        raise ValueError(f"Model ID {model_db_id} not found")

    # Get prompt template
    if prompt_id:
        prompt_row = conn.execute(
            "SELECT * FROM prompts WHERE id = ?", (prompt_id,)
        ).fetchone()
    else:
        prompt_row = conn.execute(
            "SELECT * FROM prompts ORDER BY id DESC LIMIT 1"
        ).fetchone()

    template = prompt_row["template"] if prompt_row else "{question}"

    # Collect all tasks across documents
    all_tasks = []
    render_dir = Path("data/rendered")
    for doc_id in document_ids:
        doc = get_document(conn, doc_id)
        if not doc:
            continue
        pages = get_pages(conn, doc_id)
        page_map = {p.page_number: p for p in pages}

        tasks = list_tasks(conn, doc_id)
        for task in tasks:
            if verified_only and not task.verified:
                continue
            page = page_map.get(task.page_number)
            if page:
                image_path = render_dir / page.image_path
                all_tasks.append((task, doc, str(image_path)))

        # Snapshot GT for this document
        snapshot_gt(conn, doc_id)

    if not all_tasks:
        conn.close()
        raise ValueError("No tasks to evaluate")

    # Get GT version (use first document's version)
    gt_version_id = None
    if document_ids:
        row = conn.execute(
            "SELECT id FROM gt_versions WHERE document_id = ? ORDER BY version DESC LIMIT 1",
            (document_ids[0],),
        ).fetchone()
        if row:
            gt_version_id = row["id"]

    # Create or update evaluation record
    if eval_id:
        conn.execute(
            """UPDATE evaluations
               SET model_id=?, prompt_id=?, gt_version_id=?, status='running',
                   total_tasks=?, notes=?
               WHERE id=?""",
            (model_row["model_id"], prompt_id, gt_version_id, len(all_tasks), notes, eval_id),
        )
    else:
        cur = conn.execute(
            """INSERT INTO evaluations
               (model_id, prompt_id, gt_version_id, status, total_tasks, notes)
               VALUES (?, ?, ?, 'running', ?, ?)""",
            (model_row["model_id"], prompt_id, gt_version_id, len(all_tasks), notes),
        )
        eval_id = cur.lastrowid
    conn.commit()

    # Get runner
    runner = get_runner(model_row["model_id"], model_row["provider"])

    completed = 0
    passed = 0
    total_cost = 0.0

    for task, doc, image_path in all_tasks:
        prompt = template.replace("{question}", task.question)

        try:
            response = await runner.query([image_path], prompt, str(task.id))
            parsed = parse_response(response.answer)

            cost = calculate_cost(
                response.input_tokens,
                response.output_tokens,
                model_row["input_cost_per_m"],
                model_row["output_cost_per_m"],
            )
            total_cost += cost

            # Simple scoring (full scoring engine in M005)
            task_passed = _simple_score(parsed.answer, task.expected_answer, task.scoring_method, task.tolerance)
            if task_passed:
                passed += 1

            conn.execute(
                """INSERT INTO results
                   (evaluation_id, task_id, model_answer, confidence, score,
                    passed, latency_ms, input_tokens, output_tokens, cost, raw_response)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    eval_id, task.id, parsed.answer, parsed.confidence,
                    1.0 if task_passed else 0.0, int(task_passed),
                    response.latency_ms, response.input_tokens,
                    response.output_tokens, cost,
                    json.dumps(response.raw_response),
                ),
            )
            conn.commit()

        except Exception as e:
            # Store error as result
            conn.execute(
                """INSERT INTO results
                   (evaluation_id, task_id, model_answer, passed, score, comment)
                   VALUES (?, ?, ?, 0, 0.0, ?)""",
                (eval_id, task.id, f"ERROR: {e}", str(e)),
            )
            conn.commit()

        completed += 1

        # Update evaluation progress
        conn.execute(
            """UPDATE evaluations
               SET completed_tasks = ?, passed_tasks = ?, total_cost = ?
               WHERE id = ?""",
            (completed, passed, total_cost, eval_id),
        )
        conn.commit()

        if on_progress:
            on_progress(completed, len(all_tasks), passed, total_cost)

    # Mark evaluation complete
    conn.execute(
        """UPDATE evaluations
           SET status = 'complete', completed_date = datetime('now'),
               completed_tasks = ?, passed_tasks = ?, total_cost = ?
           WHERE id = ?""",
        (completed, passed, total_cost, eval_id),
    )
    conn.commit()
    conn.close()

    return eval_id


def _simple_score(model_answer: str, expected: str, method: str, tolerance: float | None) -> bool:
    """Simple scoring — full engine in M005."""
    model_lower = model_answer.strip().lower()
    expected_lower = expected.strip().lower()

    if method == "exact":
        return model_lower == expected_lower
    elif method == "contains":
        return expected_lower in model_lower
    elif method == "numeric_tolerance":
        try:
            model_num = float(re.sub(r"[^0-9.\-]", "", model_answer))
            expected_num = float(re.sub(r"[^0-9.\-]", "", expected))
            tol = tolerance if tolerance is not None else 0.01
            return abs(model_num - expected_num) <= tol
        except (ValueError, TypeError):
            return False
    elif method == "semantic":
        # Fallback to contains for now; LLM-as-judge in M005
        return expected_lower in model_lower or model_lower in expected_lower
    return False
