"""Table ground truth routes — view and edit full table extractions."""

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from frontier.database import get_db
from frontier.models.document import get_document, get_pages
from frontier.models.table_gt import (
    delete_table_gt,
    export_json,
    get_rows,
    get_table_gt,
    get_table_gt_stats,
    import_json,
    list_table_gts,
    toggle_row_verified,
    update_cell,
)

router = APIRouter(prefix="/table-gt")


@router.get("/{doc_id}", response_class=HTMLResponse)
async def table_gt_list(request: Request, doc_id: int):
    """List all table ground truths for a document."""
    conn = get_db()
    doc = get_document(conn, doc_id)
    if not doc:
        conn.close()
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    tables = list_table_gts(conn, doc_id)
    table_info = []
    for t in tables:
        stats = get_table_gt_stats(conn, t.id)
        table_info.append({"table": t, "stats": stats})

    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "table_gt_list.html",
        {"doc": doc, "table_info": table_info},
    )


@router.get("/{doc_id}/view/{table_gt_id}", response_class=HTMLResponse)
async def table_gt_view(request: Request, doc_id: int, table_gt_id: int):
    """View and edit a table ground truth."""
    conn = get_db()
    doc = get_document(conn, doc_id)
    tgt = get_table_gt(conn, table_gt_id)
    if not doc or not tgt:
        conn.close()
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    pages = get_pages(conn, doc_id)
    rows = get_rows(conn, table_gt_id)
    stats = get_table_gt_stats(conn, table_gt_id)
    conn.close()

    current_page = pages[0] if pages else None

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "table_gt_view.html",
        {
            "doc": doc,
            "tgt": tgt,
            "columns": tgt.columns,
            "rows": rows,
            "stats": stats,
            "current_page": current_page,
            "pages": pages,
        },
    )


@router.post("/{doc_id}/import")
async def import_table_gt(
    request: Request,
    doc_id: int,
    file: UploadFile = File(...),
    table_name: str = Form(""),
):
    content = await file.read()
    conn = get_db()
    try:
        table_gt_id = import_json(
            conn, doc_id, content.decode("utf-8"),
            table_name=table_name,
            source=f"Imported from {file.filename}",
        )
        conn.close()
        return RedirectResponse(
            url=f"/table-gt/{doc_id}/view/{table_gt_id}", status_code=303
        )
    except (ValueError, Exception) as e:
        conn.close()
        return RedirectResponse(
            url=f"/table-gt/{doc_id}?error={e}", status_code=303
        )


@router.get("/{doc_id}/export/{table_gt_id}")
async def export_table_gt(doc_id: int, table_gt_id: int):
    conn = get_db()
    tgt = get_table_gt(conn, table_gt_id)
    json_str = export_json(conn, table_gt_id)
    conn.close()
    name = tgt.table_name.replace(" ", "_").lower() if tgt else "table"
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}_ground_truth.json"'},
    )


@router.post("/{doc_id}/view/{table_gt_id}/cell")
async def edit_cell(
    request: Request,
    doc_id: int,
    table_gt_id: int,
    row_id: int = Form(...),
    column: str = Form(...),
    value: str = Form(...),
):
    conn = get_db()
    update_cell(conn, row_id, column, value)
    conn.close()
    return RedirectResponse(
        url=f"/table-gt/{doc_id}/view/{table_gt_id}#row-{row_id}", status_code=303
    )


@router.post("/{doc_id}/view/{table_gt_id}/row/{row_id}/verify")
async def verify_row(request: Request, doc_id: int, table_gt_id: int, row_id: int):
    conn = get_db()
    toggle_row_verified(conn, row_id)
    conn.close()
    return RedirectResponse(
        url=f"/table-gt/{doc_id}/view/{table_gt_id}#row-{row_id}", status_code=303
    )


@router.post("/{doc_id}/view/{table_gt_id}/bulk-verify")
async def bulk_verify_rows(request: Request, doc_id: int, table_gt_id: int, row_ids: str = Form("")):
    conn = get_db()
    for rid in row_ids.split(","):
        rid = rid.strip()
        if rid.isdigit():
            conn.execute("UPDATE table_gt_rows SET verified = 1 WHERE id = ?", (int(rid),))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/table-gt/{doc_id}/view/{table_gt_id}", status_code=303)


@router.post("/{doc_id}/view/{table_gt_id}/bulk-unverify")
async def bulk_unverify_rows(request: Request, doc_id: int, table_gt_id: int, row_ids: str = Form("")):
    conn = get_db()
    for rid in row_ids.split(","):
        rid = rid.strip()
        if rid.isdigit():
            conn.execute("UPDATE table_gt_rows SET verified = 0 WHERE id = ?", (int(rid),))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/table-gt/{doc_id}/view/{table_gt_id}", status_code=303)


@router.post("/{doc_id}/delete/{table_gt_id}")
async def delete_table(request: Request, doc_id: int, table_gt_id: int):
    conn = get_db()
    delete_table_gt(conn, table_gt_id)
    conn.close()
    return RedirectResponse(url=f"/table-gt/{doc_id}", status_code=303)
