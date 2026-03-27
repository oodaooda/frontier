"""Dashboard route."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from frontier.database import get_db
from frontier.models.document import get_document_stats

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = get_db()
    doc_stats = get_document_stats(conn)

    # Task stats
    task_row = conn.execute(
        """SELECT COUNT(*) as total,
                  SUM(CASE WHEN verified=1 THEN 1 ELSE 0 END) as verified
           FROM tasks"""
    ).fetchone()

    # Recent evaluations
    recent_evals = conn.execute(
        """SELECT e.*, m.display_name as model_name
           FROM evaluations e
           LEFT JOIN models m ON e.model_id = m.model_id
           WHERE e.status = 'complete'
           ORDER BY e.started_date DESC LIMIT 5"""
    ).fetchall()

    # Best scores per model
    best_scores = conn.execute(
        """SELECT m.display_name, e.model_id,
                  MAX(e.passed_tasks * 1.0 / NULLIF(e.total_tasks, 0) * 100) as best_pct,
                  COUNT(*) as run_count
           FROM evaluations e
           LEFT JOIN models m ON e.model_id = m.model_id
           WHERE e.status = 'complete' AND e.total_tasks > 0
           GROUP BY e.model_id"""
    ).fetchall()

    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "dashboard.html",
        {
            "doc_stats": doc_stats,
            "task_total": task_row["total"],
            "task_verified": task_row["verified"] or 0,
            "recent_evals": recent_evals,
            "best_scores": best_scores,
        },
    )
