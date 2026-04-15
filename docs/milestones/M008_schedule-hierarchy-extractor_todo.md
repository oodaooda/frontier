# Milestone Todo: Schedule Hierarchy Extractor
Milestone ID: `M008`
Status: `active`
Owner: Frontier
Linked PR(s): TBD
Release tag: TBD

## Goal

Build a page-by-page schedule extractor with context tracking that maintains correct parent-child hierarchy across page breaks. Validate against verified K680 ground truth.

## Spec Reference
- `docs/specs/M008_schedule-hierarchy-extractor_prd.md`

## Phase A: Core Extractor Module
- [ ] Create `src/frontier/schedule_extractor.py`
- [ ] PDF rendering integration (reuse existing PyMuPDF utility)
- [ ] Page 1 extraction prompt — extract headers, activities, open headers at bottom
- [ ] Subsequent page extraction prompt — include carryover context
- [ ] Context tracker: store open headers after each page, pass to next page
- [ ] JSON parser for model output with error handling
- [ ] Merge per-page results into single hierarchical structure
- [ ] Build full parent path for every activity
- [ ] Output as JSON file
- [ ] Unit tests for merge logic and path building
- [ ] Commit checkpoint

## Phase B: Validation Against Ground Truth
- [ ] Load verified ground truth from Frontier database (table_gt_id=4)
- [ ] Match activities by Activity ID
- [ ] Compare extracted path vs ground truth path for each activity
- [ ] Classify errors: correct, wrong_parent, missing, extra
- [ ] Per-page accuracy breakdown
- [ ] Generate validation report JSON
- [ ] Unit tests for comparison logic
- [ ] Commit checkpoint

## Phase C: CLI Runner
- [ ] CLI command: `python -m frontier.schedule_extractor extract <pdf_path> --model claude-opus-4-6 --output result.json`
- [ ] CLI command: `python -m frontier.schedule_extractor validate <result.json> --ground-truth-id 4`
- [ ] Print summary to terminal (total accuracy, per-page breakdown, errors)
- [ ] Commit checkpoint

## Phase D: Run Against K680 Schedule
- [ ] Run extraction on K680 3-page schedule with Claude Opus 4.6
- [ ] Run validation against verified ground truth
- [ ] Document results: accuracy %, which activities were wrong, which pages had errors
- [ ] Analyze: did the context tracker maintain hierarchy across page breaks?
- [ ] Save results to `datasets/results/`
- [ ] Commit checkpoint with results

## Phase E: Integration with Frontier UI (optional)
- [ ] Add "Extract Schedule" button on document detail page
- [ ] Show extraction progress
- [ ] Display validation results in UI
- [ ] Compare extracted hierarchy vs ground truth side by side
- [ ] Commit checkpoint

## Release Gate
- [ ] Extractor produces correct JSON for K680 schedule
- [ ] Validation report shows accuracy metrics
- [ ] Context tracker demonstrably maintains hierarchy across page 1→2 and 2→3 breaks
- [ ] Results documented and committed
- [ ] Add changelog entry
