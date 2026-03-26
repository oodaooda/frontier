# Milestone Todo: Scoring, Results & Comparison Dashboard
Milestone ID: `M005`
Status: `planned`
Owner: Frontier
Linked PR(s): TBD
Release tag: TBD

## Goal

Build the scoring engine and results dashboard with scorecard views, per-question drill-down, historical comparison, and failure analysis.

## Spec Reference
- `docs/specs/M001_benchmark-platform_prd.md` (FR-4, FR-5)

## Phase A: Scoring Engine
- [ ] Exact match scorer
- [ ] Contains scorer (substring match, case-insensitive)
- [ ] Numeric tolerance scorer (configurable tolerance per task)
- [ ] Semantic similarity scorer (LLM-as-judge using a cheap/fast model)
- [ ] Score aggregation: per-tier, per-category, per-document, overall
- [ ] Human override: manually mark a result as pass/fail regardless of auto-score
- [ ] Unit tests for all scorer types with edge cases
- [ ] Commit checkpoint after Phase A

## Phase B: Results List & Scorecard
- [ ] Results list page: all past evaluation runs with summary (model, date, overall score, cost)
- [ ] Scorecard page: model × tier × category matrix with color-coded pass/fail/score
- [ ] Filter by model, date range, document
- [ ] Sort by date, score, cost
- [ ] Commit checkpoint after Phase B

## Phase C: Per-Question Drill-Down
- [ ] Run detail page: list all tasks with model answer vs. expected answer side by side
- [ ] Color coding: green (pass), red (fail), yellow (partial/uncertain)
- [ ] Show confidence score per answer
- [ ] Show latency and token count per answer
- [ ] Filter by tier, category, pass/fail, confidence level
- [ ] Commit checkpoint after Phase C

## Phase D: Comparison View
- [ ] Compare two runs side by side (same model different dates, or different models)
- [ ] Highlight regressions (was passing, now failing) and improvements
- [ ] Delta scorecard: show score changes per tier/category
- [ ] Flag if ground truth version or prompt version differs between runs
- [ ] Commit checkpoint after Phase D

## Phase E: Failure Analysis
- [ ] Filter to only failed results
- [ ] Group failures by category, tier, or document
- [ ] Identify patterns: "Model X consistently fails on schedule extraction"
- [ ] Confidence vs. correctness scatter (are low-confidence answers actually wrong?)
- [ ] Commit checkpoint after Phase E

## Phase F: Tests & Visual Baselines
- [ ] Unit tests for score aggregation and comparison logic
- [ ] Playwright tests: scorecard, drill-down, comparison, failure analysis
- [ ] Screenshot baselines for all results pages
- [ ] Manual QA from 10.0.0.5
- [ ] Commit checkpoint after Phase F

## Release Gate
- [ ] All Phase A-F checkboxes complete
- [ ] Scoring works for all four scorer types
- [ ] Scorecard renders correctly with real evaluation data
- [ ] Comparison view works for two runs
- [ ] Failure analysis filters function correctly
- [ ] Playwright tests passing
- [ ] Add changelog entry
- [ ] Merge to `main`
