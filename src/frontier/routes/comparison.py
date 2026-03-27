"""Comparison routes — side-by-side run comparison."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from frontier.database import get_db

router = APIRouter(prefix="/comparison")


@router.get("", response_class=HTMLResponse)
async def comparison_page(request: Request, run_a: int = 0, run_b: int = 0):
    conn = get_db()

    # Get all completed evaluations for selection
    evals = conn.execute(
        """SELECT e.id, e.model_id, e.started_date, e.total_tasks, e.passed_tasks, e.total_cost,
                  m.display_name as model_name
           FROM evaluations e
           LEFT JOIN models m ON e.model_id = m.model_id
           WHERE e.status = 'complete'
           ORDER BY e.started_date DESC"""
    ).fetchall()

    results_a = []
    results_b = []
    eval_a = None
    eval_b = None

    if run_a and run_b:
        eval_a = conn.execute(
            """SELECT e.*, m.display_name as model_name
               FROM evaluations e LEFT JOIN models m ON e.model_id = m.model_id
               WHERE e.id = ?""", (run_a,)
        ).fetchone()
        eval_b = conn.execute(
            """SELECT e.*, m.display_name as model_name
               FROM evaluations e LEFT JOIN models m ON e.model_id = m.model_id
               WHERE e.id = ?""", (run_b,)
        ).fetchone()

        results_a = conn.execute(
            """SELECT r.*, t.task_key, t.question, t.expected_answer, t.tier, t.category
               FROM results r JOIN tasks t ON r.task_id = t.id
               WHERE r.evaluation_id = ? ORDER BY t.id""", (run_a,)
        ).fetchall()
        results_b = conn.execute(
            """SELECT r.*, t.task_key, t.question, t.expected_answer, t.tier, t.category
               FROM results r JOIN tasks t ON r.task_id = t.id
               WHERE r.evaluation_id = ? ORDER BY t.id""", (run_b,)
        ).fetchall()

    conn.close()

    # Build comparison pairs by task_key
    b_by_key = {r["task_key"]: r for r in results_b}
    comparisons = []
    for ra in results_a:
        rb = b_by_key.get(ra["task_key"])
        change = "same"
        if rb:
            if ra["passed"] and not rb["passed"]:
                change = "regression"
            elif not ra["passed"] and rb["passed"]:
                change = "improvement"
            elif ra["passed"] and rb["passed"]:
                change = "both_pass"
            else:
                change = "both_fail"
        comparisons.append({"a": ra, "b": rb, "change": change})

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "comparison.html",
        {
            "evals": evals,
            "eval_a": eval_a,
            "eval_b": eval_b,
            "run_a": run_a,
            "run_b": run_b,
            "comparisons": comparisons,
        },
    )
