# Milestone Todo: Ground Truth Editor & Versioning
Milestone ID: `M003`
Status: `complete`
Owner: Frontier
Linked PR(s): Direct to main
Release tag: TBD

## Goal

Build the ground truth editor UI with side-by-side PDF viewing and Q&A editing, plus versioning so evaluation results always know which ground truth they were scored against.

## Spec Reference
- `docs/specs/M001_benchmark-platform_prd.md` (FR-2, FR-8)

## Phase A: Ground Truth Data Layer
- [x] Task model: CRUD for Q&A test cases (question, expected answer, scoring type, tier, category)
- [x] Verified/unverified status per task with toggle
- [x] Ground truth version tracking: auto-increment version on any task edit per document
- [x] Ground truth snapshot: store frozen copy of tasks when an evaluation run starts
- [x] YAML import: load existing ground truth YAML files into database (with duplicate detection)
- [x] YAML export: dump tasks back to YAML (backward compatible with schema)
- [x] Unit tests for task CRUD, versioning, import/export (17 tests)
- [x] Commit checkpoint after Phase A

## Phase B: Ground Truth Editor UI
- [x] Editor page layout: PDF page viewer (left panel) + Q&A list/form (right panel)
- [x] Page navigation within document (prev/next, page selector dropdown)
- [x] Display existing tasks for the current page
- [x] Create new task form: task ID, question, expected answer, scoring type, tier, category, tolerance, notes
- [x] Edit task inline (click Edit, form appears, save/cancel)
- [x] Toggle verified/unverified status
- [x] Delete task with confirmation
- [x] Commit checkpoint after Phase B

## Phase C: Import/Export & Bulk Operations
- [x] Import from YAML button on editor page
- [x] Export to YAML download button
- [x] Bulk verify: mark all tasks on a page as verified
- [x] Display current ground truth version number per document
- [x] "Edit Ground Truth" button on document detail page
- [x] Commit checkpoint after Phase C

## Phase D: Tests
- [x] Unit tests for versioning logic (17 tests for task model)
- [x] All 43 tests passing (16 database + 10 app + 17 task)
- [ ] Playwright visual tests (deferred to M006)
- [x] Manual QA: editor loads, CRUD works, import/export works
- [x] Commit checkpoint after Phase D

## Release Gate
- [x] All Phase A-D checkboxes complete (Playwright deferred)
- [x] Can create, edit, verify, delete ground truth tasks through UI
- [x] Ground truth version increments on edit
- [x] YAML import/export works with existing schema files
- [x] 43 automated tests passing
- [x] Add changelog entry
- [x] Merge to `main`
