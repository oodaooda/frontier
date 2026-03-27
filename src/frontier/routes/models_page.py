"""Model profiles routes."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from frontier.database import get_db

router = APIRouter(prefix="/models")


@router.get("", response_class=HTMLResponse)
async def models_list(request: Request):
    conn = get_db()
    models = conn.execute("SELECT * FROM models ORDER BY provider, display_name").fetchall()

    # Get eval stats per model
    model_stats = {}
    for m in models:
        row = conn.execute(
            """SELECT COUNT(*) as runs,
                      MAX(passed_tasks * 1.0 / NULLIF(total_tasks, 0) * 100) as best_score,
                      SUM(total_cost) as total_cost
               FROM evaluations WHERE model_id = ? AND status = 'complete'""",
            (m["model_id"],),
        ).fetchone()
        notes = conn.execute(
            "SELECT * FROM model_notes WHERE model_db_id = ? ORDER BY created_date DESC",
            (m["id"],),
        ).fetchall()
        model_stats[m["id"]] = {
            "runs": row["runs"] or 0,
            "best_score": round(row["best_score"] or 0),
            "total_cost": row["total_cost"] or 0,
            "notes": notes,
        }

    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "models.html",
        {"models": models, "model_stats": model_stats},
    )


@router.post("/{model_db_id}/notes")
async def add_model_note(request: Request, model_db_id: int, note: str = Form(...)):
    conn = get_db()
    conn.execute(
        "INSERT INTO model_notes (model_db_id, note) VALUES (?, ?)",
        (model_db_id, note),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/models", status_code=303)
