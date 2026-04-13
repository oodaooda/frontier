"""Prompt template management routes."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from frontier.database import get_db

router = APIRouter(prefix="/prompts")


@router.get("", response_class=HTMLResponse)
async def prompts_list(request: Request):
    conn = get_db()
    prompts = conn.execute(
        "SELECT * FROM prompts ORDER BY name, version DESC"
    ).fetchall()
    conn.close()

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "prompts.html",
        {"prompts": prompts},
    )


@router.get("/{prompt_id}/edit", response_class=HTMLResponse)
async def edit_prompt(request: Request, prompt_id: int):
    conn = get_db()
    prompt = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
    conn.close()

    if not prompt:
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "prompt_edit.html",
        {"prompt": prompt},
    )


@router.post("/{prompt_id}/update")
async def update_prompt(
    request: Request,
    prompt_id: int,
    template: str = Form(...),
):
    conn = get_db()
    conn.execute(
        "UPDATE prompts SET template = ? WHERE id = ?",
        (template, prompt_id),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/prompts", status_code=303)


@router.post("/{prompt_id}/save-as-new")
async def save_as_new_version(
    request: Request,
    prompt_id: int,
    template: str = Form(...),
):
    """Save edited template as a new version, preserving the original."""
    conn = get_db()
    original = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
    if not original:
        conn.close()
        return RedirectResponse(url="/prompts", status_code=303)

    # Get next version number for this prompt name
    max_ver = conn.execute(
        "SELECT MAX(version) as v FROM prompts WHERE name = ?",
        (original["name"],),
    ).fetchone()
    new_version = (max_ver["v"] or 0) + 1

    conn.execute(
        "INSERT INTO prompts (name, version, template) VALUES (?, ?, ?)",
        (original["name"], new_version, template),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/prompts", status_code=303)


@router.post("/create")
async def create_prompt(
    request: Request,
    name: str = Form(...),
    template: str = Form(...),
):
    conn = get_db()
    conn.execute(
        "INSERT INTO prompts (name, version, template) VALUES (?, 1, ?)",
        (name, template),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/prompts", status_code=303)


@router.post("/{prompt_id}/delete")
async def delete_prompt(request: Request, prompt_id: int):
    conn = get_db()
    conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/prompts", status_code=303)
