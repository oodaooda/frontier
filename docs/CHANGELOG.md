# Changelog

All notable milestone completions for Frontier are documented here.

## [Unreleased]

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
