"""Ground truth editor routes."""

from fastapi import APIRouter, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from frontier.database import get_db
from frontier.models.document import get_document, get_pages, list_documents
from frontier.models.task import (
    bulk_verify,
    delete_task,
    export_to_yaml,
    get_gt_version,
    get_task,
    get_task_stats,
    import_from_yaml,
    insert_task,
    list_tasks,
    toggle_verified,
    update_task,
)

router = APIRouter(prefix="/ground-truth")


@router.get("", response_class=HTMLResponse)
async def ground_truth_select(request: Request):
    conn = get_db()
    docs = list_documents(conn)
    doc_list = []
    for doc in docs:
        stats = get_task_stats(conn, doc.id)
        gt_ver = get_gt_version(conn, doc.id)
        doc_list.append({
            "doc": doc,
            "total": stats["total"],
            "verified": stats["verified"],
            "gt_version": gt_ver,
        })
    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "ground_truth_select.html",
        {"documents": doc_list},
    )


@router.get("/{doc_id}", response_class=HTMLResponse)
async def editor(request: Request, doc_id: int, page: int = 1):
    conn = get_db()
    doc = get_document(conn, doc_id)
    if not doc:
        conn.close()
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document not found")

    pages = get_pages(conn, doc_id)
    tasks = list_tasks(conn, doc_id, page_number=page)
    stats = get_task_stats(conn, doc_id)
    gt_version = get_gt_version(conn, doc_id)

    current_page = None
    for p in pages:
        if p.page_number == page:
            current_page = p
            break

    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "ground_truth_editor.html",
        {
            "doc": doc,
            "pages": pages,
            "current_page": current_page,
            "page_num": page,
            "tasks": tasks,
            "stats": stats,
            "gt_version": gt_version,
        },
    )


@router.post("/{doc_id}/tasks/create")
async def create_task(
    request: Request,
    doc_id: int,
    page_number: int = Form(...),
    task_key: str = Form(...),
    tier: int = Form(1),
    category: str = Form("table"),
    question: str = Form(...),
    expected_answer: str = Form(...),
    scoring_method: str = Form("exact"),
    tolerance: float | None = Form(None),
    notes: str = Form(""),
):
    conn = get_db()
    insert_task(
        conn, doc_id, task_key, page_number, tier, category,
        question, expected_answer, scoring_method, tolerance, notes,
    )
    conn.close()
    return RedirectResponse(
        url=f"/ground-truth/{doc_id}?page={page_number}", status_code=303
    )


@router.post("/{doc_id}/tasks/{task_id}/update")
async def update_task_route(
    request: Request,
    doc_id: int,
    task_id: int,
    question: str = Form(...),
    expected_answer: str = Form(...),
    scoring_method: str = Form("exact"),
    tier: int = Form(1),
    category: str = Form("table"),
    tolerance: float | None = Form(None),
    notes: str = Form(""),
):
    conn = get_db()
    update_task(
        conn, task_id,
        question=question,
        expected_answer=expected_answer,
        scoring_method=scoring_method,
        tier=tier,
        category=category,
        tolerance=tolerance,
        notes=notes,
    )
    task = get_task(conn, task_id)
    conn.close()
    page = task.page_number if task else 1
    return RedirectResponse(
        url=f"/ground-truth/{doc_id}?page={page}", status_code=303
    )


@router.post("/{doc_id}/tasks/{task_id}/toggle-verify")
async def toggle_verify_route(request: Request, doc_id: int, task_id: int):
    conn = get_db()
    toggle_verified(conn, task_id)
    task = get_task(conn, task_id)
    conn.close()
    page = task.page_number if task else 1
    return RedirectResponse(
        url=f"/ground-truth/{doc_id}?page={page}", status_code=303
    )


@router.post("/{doc_id}/tasks/{task_id}/delete")
async def delete_task_route(request: Request, doc_id: int, task_id: int):
    conn = get_db()
    task = get_task(conn, task_id)
    page = task.page_number if task else 1
    delete_task(conn, task_id)
    conn.close()
    return RedirectResponse(
        url=f"/ground-truth/{doc_id}?page={page}", status_code=303
    )


@router.post("/{doc_id}/bulk-verify")
async def bulk_verify_route(request: Request, doc_id: int, page: int = Form(1)):
    conn = get_db()
    bulk_verify(conn, doc_id, page)
    conn.close()
    return RedirectResponse(
        url=f"/ground-truth/{doc_id}?page={page}", status_code=303
    )


@router.get("/{doc_id}/export")
async def export_yaml(doc_id: int):
    conn = get_db()
    doc = get_document(conn, doc_id)
    yaml_str = export_to_yaml(conn, doc_id)
    conn.close()
    filename = doc.original_filename.replace(".pdf", "_ground_truth.yaml") if doc else "ground_truth.yaml"
    return Response(
        content=yaml_str,
        media_type="application/x-yaml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{doc_id}/import")
async def import_yaml(request: Request, doc_id: int, file: UploadFile = File(...)):
    content = await file.read()
    conn = get_db()
    count = import_from_yaml(conn, doc_id, content.decode("utf-8"))
    conn.close()
    return RedirectResponse(
        url=f"/ground-truth/{doc_id}?page=1", status_code=303
    )
