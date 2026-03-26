# Product Requirements Document
Milestone ID: `M001`
Title: `Benchmark Platform & Web UI`
Date: `2026-03-26`
Status: `draft`
Owner: Frontier

## Problem

Every few months, new AI models are released by Anthropic, OpenAI, Google, and others with improved vision and document understanding capabilities. There is no standardized, repeatable way to measure how well these models perform on construction-specific documents — drawings, specifications, schedules, and lookaheads.

Manual testing is slow, inconsistent, and impossible to compare across model releases. We need a formal benchmark platform that can:
- Store a curated set of construction documents
- Maintain verified ground truth for each document
- Run standardized evaluations against multiple models
- Present results in a way that makes capability gaps and improvements obvious

## Goals

1. Build a web-based UI accessible over the local network (served from deimos at 10.0.0.X, accessed from 10.0.0.5 and other machines)
2. Support uploading and managing 10-20 construction document PDFs of varying type and complexity
3. Provide a ground truth editor in the UI — view, create, edit, and correct Q&A pairs per document
4. Run model evaluations against the ground truth and store results
5. Display side-by-side model comparison to track whether the "frontier" has moved
6. Support the following document types and test categories:
   - **Plans**: floor plans, site plans — test room size estimation, spatial layout
   - **Elevations**: building elevations — test dimension reading, material identification
   - **Schedules**: door, window, finish schedules — test table extraction accuracy
   - **Complex tables**: cost breakdowns, material lists — test structured data extraction
   - **Specifications**: CSI-formatted spec sections — test cross-reference understanding
   - **Two-week lookaheads**: project schedules — test timeline/dependency reading
   - **Scaled drawings**: any drawing with a graphic or stated scale — test dimensional inference (wall lengths, room sizes from scale)

## Non-Goals

- Public-facing deployment or authentication (this is a local-network internal tool)
- Automated CI/CD pipeline for evaluations (manual trigger is fine for now)
- Support for non-PDF document formats (DWG, RVT, etc.)
- Real-time collaboration / multi-user editing
- Mobile-responsive design (desktop browser is the target)

## Functional Requirements

### FR-1: Document Management
- Upload PDF documents via the web UI
- Display a list of all uploaded documents with metadata (filename, page count, upload date, document type)
- Render and display PDF pages as images in the browser
- Assign document type tags (plan, elevation, schedule, specification, lookahead, etc.)
- Support 10-20 documents initially; design for up to 100

### FR-2: Ground Truth Management
- View rendered PDF pages alongside a ground truth Q&A editor
- Create new test cases (question + expected answer + scoring method + tier)
- Edit existing test cases inline
- Mark test cases as verified / unverified
- Support scoring types: exact match, numeric tolerance, contains, semantic similarity
- Support tiers: Tier 1 (text extraction), Tier 2 (structured understanding), Tier 3 (spatial/visual reasoning)
- Export ground truth as YAML (compatible with existing schema)

### FR-3: Model Evaluation
- Select one or more models to evaluate against a document or the full dataset
- Send rendered page images + questions to model APIs
- Store raw responses, parsed answers, latency, and token usage
- Support Anthropic (Claude) and OpenAI (GPT) as initial providers
- Handle rate limiting and retries gracefully
- Track cost per evaluation run

### FR-4: Results & Comparison
- Scorecard view: model × tier × category matrix with pass/fail/score
- Per-question drill-down: see the model's answer vs. expected answer side by side
- Historical comparison: compare the same model across different versions, or different models on the same benchmark
- Failure analysis: filter to only incorrect answers, grouped by category
- Cost and latency summary per model per run

### FR-5: Dimensional / Scale Testing
- For drawings with a stated or graphic scale, test whether the model can:
  - Estimate room sizes (e.g., "What is the approximate size of Room 101?")
  - Measure wall lengths (e.g., "What is the length of the north wall?")
  - Identify distances between grid lines or reference points
- These are Tier 3 tasks scored with numeric tolerance

### FR-6: Web UI
- Python web framework (FastAPI + Jinja2, or similar lightweight stack)
- Serve on `0.0.0.0:<port>` so it is accessible from the local network
- Simple, functional design — not a design showcase
- Key pages:
  - **Dashboard**: overview of documents, recent evaluations, summary scores
  - **Documents**: upload, list, view PDFs, manage tags
  - **Ground Truth Editor**: side-by-side PDF viewer + Q&A form
  - **Run Evaluation**: select models, select documents/dataset, trigger run
  - **Results**: scorecard, drill-down, comparison, history
  - **Run Detail**: per-question results with annotation/comment support
  - **Comparison**: side-by-side model or run comparison

### FR-7: Result Annotations & Commentary
- Per-run notes: free-text field to describe the run context (e.g., "First test with Opus 4.6 on low-res scans")
- Per-question comments: annotate individual results (e.g., "Model got count right but misread unit")
- Model-level notes: persistent notes about a model's tendencies (e.g., "GPT-5.4 struggles with fire rating columns")
- All annotations are stored persistently and visible in results views
- Filter/search results by annotation content

### FR-8: Ground Truth Versioning
- Each ground truth dataset has a version number (auto-incremented on any edit)
- Evaluation runs record which ground truth version they were scored against
- When viewing historical results, display whether the ground truth has changed since the run
- Ability to view ground truth as it existed at the time of a past run
- Prevents stale comparisons: flag results scored against outdated ground truth

### FR-9: Confidence Scoring
- Prompt templates instruct models to return a confidence level (1-5) with each answer
- Store confidence alongside the answer in results
- Display confidence in results views — surface which question types models are guessing on vs. reading clearly
- Aggregate confidence by tier/category to identify systematic weak spots

### FR-10: Prompt Versioning
- Store prompt templates with version identifiers
- Each evaluation run records which prompt version was used
- Comparison views indicate when prompt versions differ between runs
- Prevents confounding: know whether score changes came from a better prompt or a better model

### FR-11: Report Export
- Export evaluation results as a standalone HTML report (viewable without the UI)
- Export as PDF for sharing with stakeholders
- Report includes: scorecard, per-question results, model comparison, cost summary
- Include charts/visualizations for tier and category breakdowns

### FR-12: Automated Visual Testing
- Playwright-based screenshot testing of all UI pages
- Capture baseline screenshots during development
- Compare against baselines on each build to catch UI regressions
- Test all major flows: upload, edit ground truth, run evaluation, view results
- Screenshots stored in `tests/screenshots/` for review

## Acceptance Criteria

1. Can upload a construction PDF via the web UI and see its rendered pages
2. Can create, edit, and verify ground truth Q&A pairs through the UI
3. Can trigger an evaluation run against at least one model (Claude Opus 4.6)
4. Can view a scorecard showing pass/fail per question after a run
5. Can compare results from two different models (or two runs of the same model) side by side
6. UI is accessible from a browser on 10.0.0.5
7. Can add comments/annotations to individual results and to entire runs
8. Ground truth edits are versioned; results display which version they were scored against
9. Models return confidence scores; these are visible in results
10. Prompt version is recorded per run and visible in comparison views
11. Can export a results report as HTML or PDF
12. Playwright screenshot tests pass for all major UI pages

## Test Strategy

- Unit tests for scoring logic (exact match, numeric tolerance, contains, semantic)
- Unit tests for ground truth YAML serialization/deserialization
- Unit tests for ground truth versioning logic
- Integration test: upload PDF → create ground truth → run evaluation → view results
- Playwright visual regression tests: screenshot all pages, compare against baselines
- Manual QA: verify UI flows on Chrome from the remote machine
- Automated test run during each build phase (Phase G of each milestone)

## Tech Stack

| Component       | Choice                     | Rationale                                      |
|-----------------|----------------------------|------------------------------------------------|
| Backend         | Python / FastAPI            | Lightweight, async, good ecosystem             |
| Frontend        | Jinja2 templates + HTMX    | Server-rendered, minimal JS, fast to build     |
| PDF rendering   | PyMuPDF (fitz)             | Already in use, reliable                       |
| Database        | SQLite                     | Zero-config, sufficient for single-user tool   |
| Model SDKs      | anthropic, openai           | Official Python SDKs                           |
| CSS             | Pico CSS                    | Functional, no build step, classless           |
| Interactivity   | HTMX                        | Server-driven UI updates, minimal JS           |
| Visual testing  | Playwright                  | Screenshot comparison, cross-browser            |

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Model API costs during evaluation runs | Medium | High | Track costs per run; allow partial runs (subset of questions) |
| Ground truth authoring is time-consuming | High | High | Provide a good UI; allow incremental verification |
| Semantic scoring is subjective | Medium | Medium | Use LLM-as-judge with clear rubric; allow human override |
| Large PDF rendering is slow | Low | Medium | Cache rendered images; render once on upload |
| Model API rate limits during batch evaluation | Medium | Medium | Implement rate limiting, queuing, and retry logic |

## Milestone Roadmap

| ID   | Feature                                    | Status  |
|------|--------------------------------------------|---------|
| M001 | Foundation, docs & UI prototypes           | active  |
| M002 | Database layer & document management UI    | planned |
| M003 | Ground truth editor & versioning           | planned |
| M004 | Model runners & evaluation engine          | planned |
| M005 | Scoring, results & comparison dashboard    | planned |
| M006 | Annotations, export & visual testing       | planned |

### M001 — Foundation, Docs & UI Prototypes
- Project scaffolding, work tracking, PRD, milestone todos
- HTML prototypes of all UI pages for review before building
- No backend code — design review only

### M002 — Database Layer & Document Management UI
- SQLite schema, data models, migrations
- FastAPI app, base templates, navigation
- Document upload, listing, page viewer, tagging
- Playwright screenshot baselines for document pages

### M003 — Ground Truth Editor & Versioning
- Side-by-side PDF viewer + Q&A editor
- Create, edit, verify, delete test cases
- Ground truth versioning (auto-increment on edit, snapshot per run)
- YAML import/export (backward compatible)
- Playwright tests for editor flows

### M004 — Model Runners & Evaluation Engine
- Anthropic runner (Claude Opus 4.6)
- OpenAI runner (GPT-5.4)
- Prompt versioning and template management
- Confidence scoring in prompts
- Rate limiting, retries, cost tracking
- Run evaluation page with progress indicator

### M005 — Scoring, Results & Comparison Dashboard
- Scoring engine: exact match, numeric tolerance, contains, semantic (LLM-as-judge)
- Scorecard view: model × tier × category matrix
- Per-question drill-down with model answer vs. expected
- Historical comparison across runs and models
- Failure analysis filters
- Playwright tests for results pages

### M006 — Annotations, Export & Visual Testing
- Per-run and per-question annotations/comments
- Model-level notes
- HTML and PDF report export
- Full Playwright visual regression suite
- Advanced spatial/scale test cases (Tier 3)
