# Milestone Todo: Database Layer & Document Management UI
Milestone ID: `M002`
Status: `planned`
Owner: Frontier
Linked PR(s): TBD
Release tag: TBD

## Goal

Stand up the FastAPI web application with SQLite database, document upload, PDF rendering on upload, page viewing, and document tagging. This is the foundation all other UI features build on.

## Spec Reference
- `docs/specs/M001_benchmark-platform_prd.md` (FR-1, FR-6)

## Phase A: Database & Data Layer
- [ ] Define SQLite schema (documents, pages, tasks, evaluations, results, annotations)
- [ ] Database initialization script (create tables if not exist)
- [ ] Document model: insert, list, get, update, delete
- [ ] Page model: link rendered page images to documents
- [ ] Unit tests for all database CRUD operations
- [ ] Commit checkpoint after Phase A

## Phase B: FastAPI Application Shell
- [ ] FastAPI app setup with Jinja2 templates
- [ ] Serve on `0.0.0.0:8000`
- [ ] Base HTML layout template (Pico CSS, navigation bar)
- [ ] Navigation: Dashboard, Documents, Ground Truth, Evaluate, Results
- [ ] Static file serving (CSS, JS, rendered images)
- [ ] HTMX integration for dynamic updates
- [ ] Commit checkpoint after Phase B

## Phase C: Document Management Pages
- [ ] Dashboard page: document count, recent uploads summary
- [ ] Documents list page: table with filename, page count, upload date, type tags
- [ ] Document upload endpoint: accept PDF, store file, render pages, save metadata
- [ ] Document detail page: rendered page viewer with page navigation
- [ ] Document type tagging: assign/edit tags (plan, elevation, schedule, spec, lookahead)
- [ ] Delete document (with confirmation)
- [ ] Commit checkpoint after Phase C

## Phase D: Tests & Visual Baselines
- [ ] Unit tests for document upload and rendering pipeline
- [ ] Playwright setup and configuration
- [ ] Screenshot baselines: dashboard, document list, document detail, upload flow
- [ ] Manual QA: access from 10.0.0.5 browser
- [ ] Commit checkpoint after Phase D

## Release Gate
- [ ] All Phase A-D checkboxes complete
- [ ] Playwright screenshot tests passing
- [ ] UI accessible from remote machine
- [ ] At least one PDF uploaded and viewable through UI
- [ ] Add changelog entry
- [ ] Merge to `main`
