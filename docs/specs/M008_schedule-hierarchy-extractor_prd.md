# Product Requirements Document
Milestone ID: `M008`
Title: `Schedule Hierarchy Extractor`
Date: `2026-04-15`
Status: `draft`
Owner: Frontier

## Problem

Construction CPM schedules (Gantt/bar charts) span multiple pages. When AI models extract data from these schedules, they lose parent-child context at page breaks. Activities on page 2 or 3 get detached from their header groups that started on page 1. This produces incorrect or flat hierarchies that don't match the actual WBS structure.

The core challenge: **maintaining header context across page boundaries using visual cues (colored grouping bars, indentation, bold headers) that get interrupted at page breaks.**

## Goals

1. Build a Python-based extractor that reads a multi-page construction schedule PDF and outputs a hierarchical JSON with correct parent-child relationships
2. Use a page-by-page extraction with context tracking to maintain header state across pages
3. Validate the output against verified ground truth (K680 schedule: 125 rows, 116 verified)
4. Report accuracy: how many activities were assigned to the correct parent, how many were wrong
5. Identify which page breaks caused errors and why

## Non-Goals

- Gantt bar extraction (the visual timeline on the right side) — just the table data
- Predecessor/successor relationship extraction — just WBS hierarchy
- Support for every schedule format — start with P6 CPM bar charts
- Real-time processing — batch is fine

## Architecture

### Pipeline Overview

```
PDF → Render Pages → Page-by-Page Extraction → Context Tracker → Merge → Validate → JSON
```

### Step 1: PDF Rendering
- Render all pages at 400 DPI as PNG images
- Track page count

### Step 2: Page 1 Extraction (no carryover)
- Send page 1 image to the model
- Extract: all headers, subheaders, and activities with their hierarchy
- Output: structured data + list of "open headers" at the bottom of the page
- Open headers = headers whose grouping bars extend to the bottom of the page

### Step 3: Determine Open Headers
After each page extraction, determine which headers are still active:
- Ask the model: "Which grouping bars (colored vertical lines on the left) are still running at the bottom of this page? List from outermost to innermost."
- Store as `carryover_context` for the next page

### Step 4: Subsequent Page Extraction (with carryover)
For pages 2, 3, ... N:
- Send the page image to the model
- Include carryover context in the prompt: "These headers are still active from previous pages: [Level 1: CONSTRUCTION, Level 2: LLW NO.: 127569, ...]"
- The model extracts activities and assigns them to either:
  - A carryover header (activities at top of page before any new header)
  - A new header that starts on this page
  - A header that opened AND closed on this page
- After extraction, determine new open headers for the next page

### Step 5: Merge
- Combine all per-page extractions into one hierarchical JSON
- Stitch carryover headers — the same header appearing across pages becomes one node
- Assign each activity its full path (e.g., `CONSTRUCTION > LLW > 1-STOREY > WEST BUILDING`)

### Step 6: Validate Against Ground Truth
- Load the verified ground truth from the database
- For each activity (matched by Activity ID):
  - Compare extracted path vs ground truth path
  - Mark as: correct, wrong_parent, missing, extra
- Report:
  - Total activities: extracted vs expected
  - Path accuracy: % of activities with correct full parent path
  - Level accuracy: % of activities at correct depth (even if parent name differs slightly)
  - Per-page breakdown: which pages had the most errors
  - Error details: each wrong activity with expected vs actual path

## Prompt Design

### Page 1 Prompt
```
You are extracting a construction schedule from page 1 of {total_pages}.

Extract ALL rows visible on this page as JSON:
{
  "headers_and_activities": [
    {"type": "header", "level": 1, "name": "SECTION NAME"},
    {"type": "activity", "id": "A1000", "name": "...", "parent_header": "SECTION NAME",
     "original_duration": 0, "remaining_duration": 0, ...},
    ...
  ],
  "open_headers_at_bottom": [
    {"level": 1, "name": "HEADER STILL OPEN"},
    {"level": 2, "name": "SUB-HEADER STILL OPEN"}
  ]
}

Rules:
- Look at the colored vertical grouping bars on the LEFT side of the schedule
- Headers are bold/colored rows that group activities beneath them
- An "open header" is one whose grouping bar extends to the very bottom of the page
- List open headers from outermost (level 1) to innermost (deepest)
```

### Subsequent Page Prompt
```
You are extracting a construction schedule from page {n} of {total_pages}.

CARRYOVER CONTEXT from previous pages — these headers are still active:
{carryover_context}

Any activities at the TOP of this page (before a new header appears)
belong to the innermost carryover header listed above.

Extract ALL rows visible on this page. For each activity, assign it
to its correct parent header (either a carryover header or a new one
that appears on this page).

[same JSON format as page 1]
```

## Output Format

### Final JSON
```json
{
  "project": {"title": "...", "start_date": "...", "finish_date": "..."},
  "extraction_metadata": {
    "model": "claude-opus-4-6",
    "pages": 3,
    "total_activities": 116,
    "total_headers": 43,
    "extraction_time_ms": 12500,
    "cost": 0.45
  },
  "structure": [
    {
      "header": "MAJOR MILESTONES",
      "level": 1,
      "activities": [
        {"id": "A1000", "name": "Notice to Proceed", ...}
      ],
      "subheaders": [...]
    }
  ]
}
```

### Validation Report
```json
{
  "summary": {
    "total_expected": 116,
    "total_extracted": 114,
    "missing": 2,
    "extra": 0,
    "path_correct": 108,
    "path_wrong": 6,
    "path_accuracy_pct": 93.1
  },
  "errors": [
    {
      "activity_id": "A3580",
      "activity_name": "WB - Protect Structure",
      "expected_path": "CONSTRUCTION > LLW > 1-STOREY > WEST BUILDING",
      "extracted_path": "CONSTRUCTION > LLW > 1-STOREY",
      "error_type": "wrong_parent",
      "page": 3
    }
  ],
  "per_page": [
    {"page": 1, "activities": 42, "correct": 42, "wrong": 0},
    {"page": 2, "activities": 38, "correct": 35, "wrong": 3},
    {"page": 3, "activities": 36, "correct": 31, "wrong": 5}
  ]
}
```

## Tech Stack

- Python 3.11+
- Anthropic SDK (Claude Opus 4.6) — primary model
- OpenAI SDK (GPT-5.4) — for comparison
- PyMuPDF — PDF rendering
- JSON — output format
- Frontier database — ground truth source

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Model misreads visual grouping bars | High | Validate against ground truth; try higher DPI |
| Headers open and close on same page | Medium | Prompt explicitly asks about this case |
| Model output isn't valid JSON | Medium | JSON parsing with fallback, retry on failure |
| Different schedule formats have different visual conventions | Medium | Start with P6 format, generalize later |
| Cost of multi-call extraction per schedule | Low | 2-4 API calls per schedule, ~$0.50-1.00 |
