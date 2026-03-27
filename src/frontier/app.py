"""FastAPI application for the Frontier benchmark platform."""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from frontier.database import DATABASE_PATH, init_db, seed_defaults

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = Path("data/pdfs")
RENDER_DIR = Path("data/rendered")

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RENDER_DIR.mkdir(parents=True, exist_ok=True)

# Initialize database
init_db()
seed_defaults()

# FastAPI app
app = FastAPI(title="Frontier", version="0.1.0")

# Static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/rendered", StaticFiles(directory=str(RENDER_DIR)), name="rendered")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_port() -> int:
    return int(os.getenv("FRONTIER_PORT", "8000"))


# Import and include routers
from frontier.routes import (  # noqa: E402
    dashboard, documents, ground_truth, evaluate,
    results, comparison, models_page, news,
)

app.include_router(dashboard.router)
app.include_router(documents.router)
app.include_router(ground_truth.router)
app.include_router(evaluate.router)
app.include_router(results.router)
app.include_router(comparison.router)
app.include_router(models_page.router)
app.include_router(news.router)
