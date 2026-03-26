"""Document management routes."""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from frontier.database import get_db
from frontier.models.document import (
    delete_document,
    get_document,
    get_pages,
    insert_document,
    insert_page,
    list_documents,
    update_document,
)
from frontier.utils.pdf import render_pdf

router = APIRouter(prefix="/documents")


@router.get("", response_class=HTMLResponse)
async def document_list(request: Request):
    conn = get_db()
    docs = list_documents(conn)
    conn.close()

    from frontier.app import templates

    return templates.TemplateResponse(
        request, "documents.html",
        {"documents": docs},
    )


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = Form(""),
):
    from frontier.app import UPLOAD_DIR, RENDER_DIR

    # Save uploaded file with unique name
    ext = Path(file.filename).suffix
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / stored_name
    with open(dest, "wb") as f:
        content = await file.read()
        f.write(content)

    file_size = dest.stat().st_size

    # Render PDF pages
    render_output = render_pdf(str(dest), dpi=300, output_dir=str(RENDER_DIR / stored_name.replace(ext, "")))
    import os
    page_files = sorted(
        [f for f in os.listdir(render_output) if f.endswith(".png")]
    )
    page_count = len(page_files)

    # Insert into database
    conn = get_db()
    doc_id = insert_document(
        conn,
        filename=stored_name,
        original_filename=file.filename,
        file_size=file_size,
        page_count=page_count,
        doc_type=doc_type,
    )

    # Insert page records
    for i, page_file in enumerate(page_files, 1):
        image_path = f"{stored_name.replace(ext, '')}/{page_file}"
        from PIL import Image
        img = Image.open(render_output / page_file)
        w, h = img.size
        img.close()
        insert_page(conn, doc_id, i, image_path, w, h)

    conn.close()

    return RedirectResponse(url=f"/documents/{doc_id}", status_code=303)


@router.get("/{doc_id}", response_class=HTMLResponse)
async def document_detail(request: Request, doc_id: int, page: int = 1):
    conn = get_db()
    doc = get_document(conn, doc_id)
    if not doc:
        conn.close()
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document not found")

    pages = get_pages(conn, doc_id)
    conn.close()

    current_page = None
    for p in pages:
        if p.page_number == page:
            current_page = p
            break

    from frontier.app import templates

    return templates.TemplateResponse(
        request, "document_detail.html",
        {
            "doc": doc,
            "pages": pages,
            "current_page": current_page,
            "page_num": page,
        },
    )


@router.post("/{doc_id}/tag")
async def update_tag(request: Request, doc_id: int, doc_type: str = Form(...)):
    conn = get_db()
    update_document(conn, doc_id, doc_type=doc_type)
    conn.close()
    return RedirectResponse(url=f"/documents/{doc_id}", status_code=303)


@router.post("/{doc_id}/delete")
async def delete_doc(request: Request, doc_id: int):
    conn = get_db()
    doc = get_document(conn, doc_id)
    if doc:
        # Clean up files
        from frontier.app import UPLOAD_DIR, RENDER_DIR

        pdf_path = UPLOAD_DIR / doc.filename
        if pdf_path.exists():
            pdf_path.unlink()
        render_dir = RENDER_DIR / doc.filename.rsplit(".", 1)[0]
        if render_dir.exists():
            shutil.rmtree(render_dir)

        delete_document(conn, doc_id)
    conn.close()
    return RedirectResponse(url="/documents", status_code=303)
