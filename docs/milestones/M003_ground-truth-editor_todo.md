# Milestone Todo: Ground Truth Editor & Versioning
Milestone ID: `M003`
Status: `planned`
Owner: Frontier
Linked PR(s): TBD
Release tag: TBD

## Goal

Build the ground truth editor UI with side-by-side PDF viewing and Q&A editing, plus versioning so evaluation results always know which ground truth they were scored against.

## Spec Reference
- `docs/specs/M001_benchmark-platform_prd.md` (FR-2, FR-8)

## Phase A: Ground Truth Data Layer
- [ ] Task model: CRUD for Q&A test cases (question, expected answer, scoring type, tier, category)
- [ ] Verified/unverified status per task
- [ ] Ground truth version tracking: auto-increment version on any task edit per document
- [ ] Ground truth snapshot: store frozen copy of tasks when an evaluation run starts
- [ ] YAML import: load existing ground truth YAML files into database
- [ ] YAML export: dump tasks back to YAML (backward compatible with schema)
- [ ] Unit tests for task CRUD, versioning, import/export
- [ ] Commit checkpoint after Phase A

## Phase B: Ground Truth Editor UI
- [ ] Editor page layout: PDF page viewer (left panel) + Q&A list/form (right panel)
- [ ] Page navigation within document (prev/next, page selector)
- [ ] Display existing tasks for the current page
- [ ] Create new task form: question, expected answer, scoring type dropdown, tier dropdown, category dropdown
- [ ] Edit task inline (click to edit, save/cancel)
- [ ] Toggle verified/unverified status
- [ ] Delete task with confirmation
- [ ] HTMX: add/edit/delete without full page reload
- [ ] Commit checkpoint after Phase B

## Phase C: Import/Export & Bulk Operations
- [ ] Import from YAML button on document detail page
- [ ] Export to YAML button
- [ ] Bulk verify: mark all tasks on a page as verified
- [ ] Display current ground truth version number per document
- [ ] Commit checkpoint after Phase C

## Phase D: Tests & Visual Baselines
- [ ] Unit tests for versioning logic (edit → version increments, snapshot freezes)
- [ ] Playwright tests: create task, edit task, delete task, verify task
- [ ] Playwright tests: import YAML, export YAML
- [ ] Screenshot baselines for editor page layouts
- [ ] Manual QA: full ground truth editing workflow from 10.0.0.5
- [ ] Commit checkpoint after Phase D

## Release Gate
- [ ] All Phase A-D checkboxes complete
- [ ] Can create, edit, verify, delete ground truth tasks through UI
- [ ] Ground truth version increments on edit
- [ ] YAML import/export works with existing schema files
- [ ] Playwright tests passing
- [ ] Add changelog entry
- [ ] Merge to `main`
