"""Evaluation routes — run models against ground truth."""

import asyncio
import threading

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from frontier.database import get_db
from frontier.models.document import list_documents

router = APIRouter(prefix="/evaluate")

# Track running evaluations
_running_evals: dict[int, dict] = {}


@router.get("", response_class=HTMLResponse)
async def evaluate_page(request: Request):
    conn = get_db()
    docs = list_documents(conn)
    models = conn.execute("SELECT * FROM models WHERE status = 'active'").fetchall()
    prompts = conn.execute("SELECT * FROM prompts ORDER BY name, version DESC").fetchall()

    # Get task counts per document
    doc_info = []
    for doc in docs:
        row = conn.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN verified=1 THEN 1 ELSE 0 END) as verified FROM tasks WHERE document_id=?",
            (doc.id,),
        ).fetchone()
        doc_info.append({
            "doc": doc,
            "total_tasks": row["total"],
            "verified_tasks": row["verified"] or 0,
        })

    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "evaluate.html",
        {"doc_info": doc_info, "models": models, "prompts": prompts},
    )


@router.post("/run")
async def run_evaluation_route(
    request: Request,
    model_id: int = Form(...),
    document_ids: list[int] = Form(...),
    prompt_id: int = Form(None),
    verified_only: bool = Form(True),
    notes: str = Form(""),
):
    from frontier.evaluation import run_evaluation

    # Validate API key before starting
    conn = get_db()
    model_row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    conn.close()

    if model_row:
        import os
        provider = model_row["provider"]
        if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            return RedirectResponse(
                url="/evaluate?error=ANTHROPIC_API_KEY not set in .env file", status_code=303
            )
        if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            return RedirectResponse(
                url="/evaluate?error=OPENAI_API_KEY not set in .env file", status_code=303
            )

    # Create the evaluation record first to get an ID
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO evaluations (model_id, prompt_id, status, total_tasks, notes)
           VALUES (?, ?, 'starting', 0, ?)""",
        (model_row["model_id"] if model_row else "unknown", prompt_id, notes),
    )
    eval_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Track progress
    _running_evals[eval_id] = {
        "completed": 0, "total": 0, "passed": 0, "cost": 0.0, "status": "starting"
    }

    def progress_callback(completed, total, passed, cost):
        _running_evals[eval_id] = {
            "completed": completed, "total": total, "passed": passed,
            "cost": cost, "status": "running"
        }

    # Run in background thread with its own event loop
    def run_in_thread():
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_evaluation(
                model_db_id=model_id,
                document_ids=document_ids,
                prompt_id=prompt_id if prompt_id else None,
                verified_only=verified_only,
                notes=notes,
                on_progress=progress_callback,
                eval_id=eval_id,
            ))
            _running_evals[eval_id]["status"] = "complete"
        except Exception as e:
            _running_evals[eval_id]["status"] = f"error: {e}"
            # Update DB
            conn = get_db()
            conn.execute(
                "UPDATE evaluations SET status = 'error', notes = ? WHERE id = ?",
                (f"{notes}\nError: {e}" if notes else f"Error: {e}", eval_id),
            )
            conn.commit()
            conn.close()
        finally:
            loop.close()

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()

    return RedirectResponse(url=f"/evaluate/progress/{eval_id}", status_code=303)


@router.get("/progress/{eval_id}", response_class=HTMLResponse)
async def progress_page(request: Request, eval_id: int):
    conn = get_db()
    evaluation = conn.execute(
        """SELECT e.*, m.display_name as model_name
           FROM evaluations e
           LEFT JOIN models m ON e.model_id = m.model_id
           WHERE e.id = ?""",
        (eval_id,),
    ).fetchone()
    conn.close()

    if not evaluation:
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "evaluate_progress.html",
        {"evaluation": evaluation, "eval_id": eval_id},
    )


@router.get("/progress/{eval_id}/status", response_class=JSONResponse)
async def progress_status(eval_id: int):
    """API endpoint for polling progress."""
    # Check in-memory progress first
    if eval_id in _running_evals:
        return _running_evals[eval_id]

    # Fall back to DB
    conn = get_db()
    row = conn.execute(
        "SELECT status, completed_tasks, total_tasks, passed_tasks, total_cost FROM evaluations WHERE id = ?",
        (eval_id,),
    ).fetchone()
    conn.close()

    if not row:
        return {"status": "not_found"}

    return {
        "completed": row["completed_tasks"],
        "total": row["total_tasks"],
        "passed": row["passed_tasks"],
        "cost": row["total_cost"],
        "status": row["status"],
    }
