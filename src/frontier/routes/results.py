"""Results routes — view evaluation outcomes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from frontier.database import get_db

router = APIRouter(prefix="/results")


@router.get("", response_class=HTMLResponse)
async def results_list(request: Request):
    conn = get_db()
    evals = conn.execute(
        """SELECT e.*, m.display_name as model_name, m.provider,
                  p.name as prompt_name, p.version as prompt_version
           FROM evaluations e
           LEFT JOIN models m ON e.model_id = m.model_id
           LEFT JOIN prompts p ON e.prompt_id = p.id
           ORDER BY e.started_date DESC"""
    ).fetchall()
    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "results_list.html",
        {"evaluations": evals},
    )


@router.get("/{eval_id}", response_class=HTMLResponse)
async def result_detail(request: Request, eval_id: int):
    conn = get_db()

    evaluation = conn.execute(
        """SELECT e.*, m.display_name as model_name, m.provider
           FROM evaluations e
           LEFT JOIN models m ON e.model_id = m.model_id
           WHERE e.id = ?""",
        (eval_id,),
    ).fetchone()

    if not evaluation:
        conn.close()
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Evaluation not found")

    results = conn.execute(
        """SELECT r.*, t.task_key, t.question, t.expected_answer, t.tier,
                  t.category, t.scoring_method, t.page_number,
                  d.original_filename as doc_name
           FROM results r
           JOIN tasks t ON r.task_id = t.id
           JOIN documents d ON t.document_id = d.id
           WHERE r.evaluation_id = ?
           ORDER BY t.document_id, t.page_number, t.id""",
        (eval_id,),
    ).fetchall()

    # Compute tier scores
    tier_stats = {}
    for r in results:
        tier = r["tier"]
        if tier not in tier_stats:
            tier_stats[tier] = {"total": 0, "passed": 0}
        tier_stats[tier]["total"] += 1
        if r["passed"]:
            tier_stats[tier]["passed"] += 1

    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "result_detail.html",
        {
            "evaluation": evaluation,
            "results": results,
            "tier_stats": tier_stats,
        },
    )


@router.post("/{eval_id}/results/{result_id}/comment")
async def add_comment(request: Request, eval_id: int, result_id: int):
    form = await request.form()
    comment = form.get("comment", "")
    conn = get_db()
    conn.execute("UPDATE results SET comment = ? WHERE id = ?", (comment, result_id))
    conn.commit()
    conn.close()
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/results/{eval_id}", status_code=303)


@router.post("/{eval_id}/notes")
async def update_notes(request: Request, eval_id: int):
    form = await request.form()
    notes = form.get("notes", "")
    conn = get_db()
    conn.execute("UPDATE evaluations SET notes = ? WHERE id = ?", (notes, eval_id))
    conn.commit()
    conn.close()
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/results/{eval_id}", status_code=303)
