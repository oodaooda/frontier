"""Table extraction evaluation routes."""

import asyncio
import json
import threading

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from frontier.database import get_db
from frontier.models.document import get_document, list_documents
from frontier.models.table_gt import get_table_gt, get_table_gt_stats, list_table_gts

router = APIRouter(prefix="/table-eval")

_running: dict[str, dict] = {}


@router.get("", response_class=HTMLResponse)
async def table_eval_page(request: Request):
    conn = get_db()
    models = conn.execute("SELECT * FROM models WHERE status = 'active'").fetchall()
    docs = list_documents(conn)

    # Get table GTs per document
    doc_tables = []
    for doc in docs:
        tables = list_table_gts(conn, doc.id)
        for t in tables:
            stats = get_table_gt_stats(conn, t.id)
            doc_tables.append({"doc": doc, "table": t, "stats": stats})

    # Past table extraction results
    past_results = conn.execute(
        """SELECT id, model_id, total_tasks, passed_tasks, total_cost, notes, started_date
           FROM evaluations
           WHERE notes LIKE '%table_gt_id%' AND status = 'complete'
           ORDER BY started_date DESC LIMIT 20"""
    ).fetchall()

    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "table_eval.html",
        {
            "models": models,
            "doc_tables": doc_tables,
            "past_results": past_results,
        },
    )


@router.post("/run")
async def run_table_eval(
    request: Request,
    model_id: int = Form(...),
    document_id: int = Form(...),
    table_gt_id: int = Form(...),
):
    import os
    conn = get_db()
    model_row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    conn.close()

    if model_row:
        provider = model_row["provider"]
        if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            return RedirectResponse(url="/table-eval?error=ANTHROPIC_API_KEY+not+set", status_code=303)
        if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            return RedirectResponse(url="/table-eval?error=OPENAI_API_KEY+not+set", status_code=303)

    run_key = f"{model_id}-{table_gt_id}"
    _running[run_key] = {"status": "running"}

    def run_in_thread():
        from frontier.table_evaluation import run_table_extraction
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                run_table_extraction(model_id, document_id, table_gt_id)
            )
            _running[run_key] = {"status": "complete", "result": result}
        except Exception as e:
            _running[run_key] = {"status": f"error: {e}"}
        finally:
            loop.close()

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()

    return RedirectResponse(
        url=f"/table-eval/progress?key={run_key}&doc_id={document_id}&table_gt_id={table_gt_id}",
        status_code=303,
    )


@router.get("/progress", response_class=HTMLResponse)
async def progress_page(request: Request, key: str = "", doc_id: int = 0, table_gt_id: int = 0):
    from frontier.app import templates
    return templates.TemplateResponse(
        request, "table_eval_progress.html",
        {"key": key, "doc_id": doc_id, "table_gt_id": table_gt_id},
    )


@router.get("/progress/status")
async def progress_status(key: str = ""):
    if key in _running:
        info = _running[key]
        if info["status"] == "complete" and "result" in info:
            return {
                "status": "complete",
                "eval_id": info["result"].get("eval_id"),
                "accuracy": info["result"].get("accuracy"),
                "matched": info["result"].get("matched_cells"),
                "total": info["result"].get("total_cells"),
                "cost": info["result"].get("cost", 0),
                "error": info["result"].get("error"),
            }
        return {"status": info["status"]}
    return {"status": "not_found"}


@router.get("/result/{eval_id}", response_class=HTMLResponse)
async def table_eval_result(request: Request, eval_id: int):
    conn = get_db()
    evaluation = conn.execute(
        "SELECT * FROM evaluations WHERE id = ?", (eval_id,)
    ).fetchone()
    conn.close()

    if not evaluation or not evaluation["notes"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    try:
        result_data = json.loads(evaluation["notes"])
    except json.JSONDecodeError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Invalid result data")

    # Group cell results by row for display
    columns = list(result_data.get("column_accuracy", {}).keys())
    cell_map = {}
    for c in result_data.get("cell_results", []):
        cell_map.setdefault(c["row"], {})[c["col"]] = c

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "table_eval_result.html",
        {
            "evaluation": evaluation,
            "result": result_data,
            "columns": columns,
            "cell_map": cell_map,
            "max_rows": max(
                result_data.get("expected_row_count", 0),
                result_data.get("model_row_count", 0),
            ),
        },
    )
