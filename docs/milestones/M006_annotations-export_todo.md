# Milestone Todo: Annotations, Export & Visual Testing
Milestone ID: `M006`
Status: `planned`
Owner: Frontier
Linked PR(s): TBD
Release tag: TBD

## Goal

Add result annotations/commentary, report export (HTML/PDF), complete the Playwright visual regression suite, and build out advanced Tier 3 spatial/scale test cases.

## Spec Reference
- `docs/specs/M001_benchmark-platform_prd.md` (FR-7, FR-11, FR-12, FR-5)

## Phase A: Annotations & Commentary
- [ ] Per-run notes: free-text field on run detail page
- [ ] Per-question comments: add/edit comment on individual results
- [ ] Model-level notes: persistent notes page per model (tendencies, known weaknesses)
- [ ] Display annotations in results views and comparison views
- [ ] Search/filter results by annotation content
- [ ] Unit tests for annotation CRUD
- [ ] Commit checkpoint after Phase A

## Phase B: Report Export
- [ ] HTML report template: scorecard, per-question results, comparison, cost summary
- [ ] Generate standalone HTML report (no server dependency, embedded CSS)
- [ ] PDF export (via HTML-to-PDF, e.g., weasyprint or playwright pdf)
- [ ] Include charts: tier breakdown bar chart, category breakdown, confidence distribution
- [ ] Download button on results and comparison pages
- [ ] Unit tests for report generation
- [ ] Commit checkpoint after Phase B

## Phase C: Advanced Spatial/Scale Test Cases
- [ ] Define Tier 3 test case templates for scaled drawings
- [ ] Room size estimation tasks (e.g., "What is the approximate area of Room 101?")
- [ ] Wall length measurement tasks (e.g., "What is the length of the north wall?")
- [ ] Grid line distance tasks (e.g., "What is the distance between gridline A and B?")
- [ ] Document scale identification tasks (e.g., "What is the drawing scale?")
- [ ] Numeric tolerance scoring calibration for dimensional tasks
- [ ] Add 10-15 spatial test cases across uploaded drawings
- [ ] Commit checkpoint after Phase C

## Phase D: Full Visual Regression Suite
- [ ] Playwright test coverage for every page in the application
- [ ] Screenshot baselines stored in `tests/screenshots/`
- [ ] Comparison script: diff current screenshots against baselines
- [ ] CI-friendly test runner (can run headless, returns exit code)
- [ ] Document how to update baselines after intentional UI changes
- [ ] Commit checkpoint after Phase D

## Phase E: Polish & QA
- [ ] End-to-end walkthrough: upload → ground truth → evaluate → results → annotate → export
- [ ] Cross-browser check (Chrome, Firefox) from 10.0.0.5
- [ ] Performance check: 20 documents, 100+ tasks, multiple runs
- [ ] Fix any UI inconsistencies found in walkthrough
- [ ] Commit checkpoint after Phase E

## Release Gate
- [ ] All Phase A-E checkboxes complete
- [ ] Annotations visible and searchable in results views
- [ ] HTML and PDF reports generate correctly
- [ ] Tier 3 spatial test cases added and scoreable
- [ ] Full Playwright visual regression suite passing
- [ ] End-to-end walkthrough passes
- [ ] Add changelog entry
- [ ] Merge to `main`
