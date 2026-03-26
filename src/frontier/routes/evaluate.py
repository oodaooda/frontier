"""Evaluation routes — run models against ground truth."""

import asyncio

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from frontier.database import get_db
from frontier.models.document import list_documents

router = APIRouter(prefix="/evaluate")


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

    try:
        eval_id = await run_evaluation(
            model_db_id=model_id,
            document_ids=document_ids,
            prompt_id=prompt_id if prompt_id else None,
            verified_only=verified_only,
            notes=notes,
        )
        return RedirectResponse(url=f"/results/{eval_id}", status_code=303)
    except ValueError as e:
        # Redirect back with error
        return RedirectResponse(url=f"/evaluate?error={e}", status_code=303)
