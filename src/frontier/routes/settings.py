"""Settings routes — API keys, RSS feeds, database backup."""

import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from frontier.database import DATABASE_PATH, get_db

router = APIRouter(prefix="/settings")

BACKUP_DIR = Path("data/backups")


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request):
    conn = get_db()
    models = conn.execute("SELECT * FROM models ORDER BY provider").fetchall()
    feeds = conn.execute("SELECT * FROM rss_feeds ORDER BY provider").fetchall()
    conn.close()

    # Check API keys
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")

    # List backups
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = sorted(BACKUP_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)

    from frontier.app import templates
    return templates.TemplateResponse(
        request, "settings.html",
        {
            "models": models,
            "feeds": feeds,
            "anthropic_key_set": bool(anthropic_key),
            "openai_key_set": bool(openai_key),
            "anthropic_key_masked": f"...{anthropic_key[-8:]}" if len(anthropic_key) > 8 else ("set" if anthropic_key else "not set"),
            "openai_key_masked": f"...{openai_key[-8:]}" if len(openai_key) > 8 else ("set" if openai_key else "not set"),
            "backups": backups,
            "db_path": str(DATABASE_PATH),
        },
    )


@router.post("/backup")
async def create_backup(request: Request):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"frontier_{timestamp}.db"
    shutil.copy2(str(DATABASE_PATH), str(dest))
    return RedirectResponse(url="/settings?msg=Backup+created", status_code=303)


@router.post("/rss/poll")
async def poll_rss(request: Request):
    from frontier.rss import poll_all_feeds
    results = poll_all_feeds()
    total = sum(v for v in results.values() if isinstance(v, int))
    return RedirectResponse(
        url=f"/settings?msg=Polled+feeds:+{total}+new+entries", status_code=303
    )


@router.post("/models/add")
async def add_model(
    request: Request,
    model_id: str = Form(...),
    provider: str = Form(...),
    display_name: str = Form(...),
    input_cost_per_m: float = Form(0.0),
    output_cost_per_m: float = Form(0.0),
):
    conn = get_db()
    conn.execute(
        """INSERT OR IGNORE INTO models (model_id, provider, display_name, input_cost_per_m, output_cost_per_m)
           VALUES (?, ?, ?, ?, ?)""",
        (model_id, provider, display_name, input_cost_per_m, output_cost_per_m),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/settings?msg=Model+added", status_code=303)


@router.post("/feeds/add")
async def add_feed(
    request: Request,
    name: str = Form(...),
    url: str = Form(...),
    provider: str = Form(...),
):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO rss_feeds (name, url, provider) VALUES (?, ?, ?)",
        (name, url, provider),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/settings?msg=Feed+added", status_code=303)
