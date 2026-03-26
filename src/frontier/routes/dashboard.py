"""Dashboard route."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from frontier.database import get_db
from frontier.models.document import get_document_stats

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = get_db()
    stats = get_document_stats(conn)
    conn.close()

    from frontier.app import templates

    return templates.TemplateResponse(
        request, "dashboard.html",
        {"stats": stats},
    )
