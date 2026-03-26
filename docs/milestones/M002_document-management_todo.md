# Milestone Todo: Database Layer & Document Management UI
Milestone ID: `M002`
Status: `complete`
Owner: Frontier
Linked PR(s): Direct to main
Release tag: TBD

## Goal

Stand up the FastAPI web application with SQLite database, document upload, PDF rendering on upload, page viewing, and document tagging. This is the foundation all other UI features build on.

## Spec Reference
- `docs/specs/M001_benchmark-platform_prd.md` (FR-1, FR-6)

## Phase A: Database & Data Layer
- [x] Define SQLite schema (documents, pages, tasks, evaluations, results, annotations)
- [x] Database initialization script (create tables if not exist)
- [x] Document model: insert, list, get, update, delete
- [x] Page model: link rendered page images to documents
- [x] Unit tests for all database CRUD operations (16 tests)
- [x] Commit checkpoint after Phase A

## Phase B: FastAPI Application Shell
- [x] FastAPI app setup with Jinja2 templates
- [x] Serve on `0.0.0.0:8000`
- [x] Base HTML layout template (Pico CSS, navigation bar)
- [x] Navigation: Dashboard, Documents, Ground Truth, Evaluate, Results, Comparison, Models, News, Prompt Lab, Trends
- [x] Static file serving (CSS, JS, rendered images)
- [x] HTMX integration for dynamic updates
- [x] Dark mode toggle
- [x] Commit checkpoint after Phase B

## Phase C: Document Management Pages
- [x] Dashboard page: document count, type breakdown
- [x] Documents list page: table with filename, page count, upload date, type tags
- [x] Document upload endpoint: accept PDF, store file, render pages at 300 DPI, save metadata
- [x] Document detail page: rendered page viewer with page navigation
- [x] Document type tagging: assign/edit tags (plan, elevation, schedule, spec, lookahead, table)
- [x] Delete document (with confirmation)
- [x] Commit checkpoint after Phase C

## Phase D: Tests & Visual Baselines
- [x] Unit tests for database CRUD (16 tests)
- [x] Integration tests for app routes (10 tests)
- [x] All 26 tests passing
- [ ] Playwright screenshot baselines (deferred to M006)
- [x] Manual QA: app runs and serves pages correctly
- [x] Commit checkpoint after Phase D

## Release Gate
- [x] All Phase A-D checkboxes complete (Playwright deferred)
- [ ] Playwright screenshot tests passing (deferred to M006)
- [x] UI accessible from remote machine (0.0.0.0:8000)
- [x] PDF uploaded and viewable through UI (A700_door_schedule.pdf)
- [x] Add changelog entry
- [x] Merge to `main`
