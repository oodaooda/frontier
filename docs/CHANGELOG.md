# Changelog

All notable milestone completions for Frontier are documented here.

## [Unreleased]

### M007 — RSS Feeds, Settings & Backup (2026-03-27)
- RSS feed polling with keyword filtering for model release news
- Settings page: API key status, model management, RSS feed management
- Database backup on demand with backup history
- Add new models and RSS feeds through the UI
- Poll all feeds button with new entry count

### M006 — Dashboard, Export & Delete (2026-03-27)
- Enhanced dashboard with real stats, recent evals, model leaderboard
- HTML report export (standalone downloadable file)
- Delete evaluation runs with cascade
- Compare button on result detail page

### M005 — Comparison & All Pages (2026-03-27)
- Side-by-side run comparison with per-question diff
- Ground Truth selector page
- Models page with eval stats and persistent notes
- News/Model Intel page with add/status tracking
- All nav links wired to functional pages

### Scope Gap Fixes (2026-03-27)
- File upload: JS click delegation + Fetch API (Pico CSS fix)
- Async evaluation with progress page and polling
- API key validation before evaluation runs

### M004 — Model Runners & Evaluation Engine (2026-03-26)
- Anthropic runner (Claude) with vision support
- OpenAI runner (GPT) with vision support
- Evaluation pipeline: iterate tasks, call model, parse response, score, store
- Response parsing: extract Answer and Confidence from model output
- Simple scoring: exact, contains, numeric_tolerance, semantic
- Cost calculation per request based on model pricing
- Evaluate page: select model, documents, prompt, run
- Results list and per-question drill-down with comments
- Run notes and per-result annotations
- 58 automated tests

### M003 — Ground Truth Editor & Versioning (2026-03-26)
- Side-by-side PDF viewer + Q&A editor with inline editing
- Task CRUD: create, edit, verify, delete ground truth tasks
- GT versioning: auto-increment on any edit, snapshot for evaluation runs
- YAML import/export backward compatible with existing schema
- Bulk verify all tasks on a page
- 43 automated tests (17 task model + 16 database + 10 app)

### M002 — Database Layer & Document Management UI (2026-03-26)
- SQLite database with 10 tables covering full data model
- FastAPI web app serving on 0.0.0.0:8000
- Document upload with PDF rendering at 300 DPI
- Document list, detail view with page navigation
- Document type tagging and deletion
- 26 automated tests (16 unit, 10 integration)

### M001 — Foundation, Docs & UI Prototypes (2026-03-26)
- Project scaffolding and initial structure
- PRD with 12 functional requirements
- 7 milestone todos (M001-M007) with phased checklists
- 12 UI prototype pages with dark mode toggle
- .env.example template for API key configuration
