"""News / Model Intel routes."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from frontier.database import get_db

router = APIRouter(prefix="/news")


@router.get("", response_class=HTMLResponse)
async def news_list(request: Request):
    conn = get_db()
    entries = conn.execute(
        "SELECT * FROM news ORDER BY created_date DESC"
    ).fetchall()
    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "news.html", {"entries": entries},
    )


@router.post("/add")
async def add_entry(
    request: Request,
    headline: str = Form(...),
    provider: str = Form(...),
    entry_type: str = Form("release"),
    body: str = Form(""),
    relevance: str = Form(""),
    source_url: str = Form(""),
):
    conn = get_db()
    conn.execute(
        """INSERT INTO news (headline, provider, entry_type, body, relevance, source_url, status)
           VALUES (?, ?, ?, ?, ?, ?, 'new')""",
        (headline, provider, entry_type, body, relevance, source_url),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/news", status_code=303)


@router.post("/{entry_id}/status")
async def update_status(request: Request, entry_id: int, status: str = Form(...)):
    conn = get_db()
    conn.execute("UPDATE news SET status = ? WHERE id = ?", (status, entry_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/news", status_code=303)
