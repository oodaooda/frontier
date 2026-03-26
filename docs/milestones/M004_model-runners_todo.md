# Milestone Todo: Model Runners & Evaluation Engine
Milestone ID: `M004`
Status: `planned`
Owner: Frontier
Linked PR(s): TBD
Release tag: TBD

## Goal

Implement model API integrations for Anthropic (Claude) and OpenAI (GPT), prompt versioning, confidence scoring, and the evaluation run pipeline with progress tracking.

## Spec Reference
- `docs/specs/M001_benchmark-platform_prd.md` (FR-3, FR-9, FR-10)

## Phase A: Model Runner Abstraction
- [ ] Refine BaseRunner interface (async query, model_id, cost calculation)
- [ ] Runner registry: register/discover available runners by provider
- [ ] API key management: load from `.env` file, validate on startup
- [ ] Commit checkpoint after Phase A

## Phase B: Anthropic Runner
- [ ] Anthropic runner: send rendered page images + prompt via anthropic SDK
- [ ] Handle vision/image content blocks
- [ ] Parse response: extract answer text, token usage, latency
- [ ] Cost calculation based on model pricing
- [ ] Rate limiting: respect API limits, queue requests
- [ ] Retry logic with exponential backoff
- [ ] Unit tests with mocked API responses
- [ ] Commit checkpoint after Phase B

## Phase C: OpenAI Runner
- [ ] OpenAI runner: send rendered page images + prompt via openai SDK
- [ ] Handle vision/image content in OpenAI format
- [ ] Parse response: extract answer text, token usage, latency
- [ ] Cost calculation based on model pricing
- [ ] Rate limiting and retry logic
- [ ] Unit tests with mocked API responses
- [ ] Commit checkpoint after Phase C

## Phase D: Prompt Management
- [ ] Prompt template storage in database (name, version, template text)
- [ ] Default prompt templates (one per tier/category or a universal template)
- [ ] Confidence scoring instruction in prompts ("Rate your confidence 1-5")
- [ ] Parse confidence score from model response
- [ ] Prompt editor page in UI: view, create, edit prompt templates
- [ ] Commit checkpoint after Phase D

## Phase E: Evaluation Pipeline
- [ ] Evaluation run model: store run metadata (model, prompt version, ground truth version, timestamp)
- [ ] Result model: store per-task answer, confidence, score, latency, tokens, cost
- [ ] Run evaluation page: select model(s), select document(s), select prompt template, trigger run
- [ ] Evaluation executor: iterate tasks, call runner, store results
- [ ] Progress indicator: show completion percentage during run (HTMX polling or SSE)
- [ ] Cost summary after run completes
- [ ] Partial runs: evaluate a subset of tasks or documents
- [ ] Commit checkpoint after Phase E

## Phase F: Tests
- [ ] Integration test: trigger evaluation → results stored correctly
- [ ] Unit tests for cost calculation
- [ ] Unit tests for prompt template versioning
- [ ] Unit tests for confidence score parsing
- [ ] Playwright tests: run evaluation page, progress indicator
- [ ] Commit checkpoint after Phase F

## Release Gate
- [ ] All Phase A-F checkboxes complete
- [ ] Can run evaluation against Claude Opus 4.6 with real API key
- [ ] Can run evaluation against GPT-5.4 with real API key
- [ ] Prompt version and ground truth version recorded per run
- [ ] Confidence scores captured and stored
- [ ] Playwright tests passing
- [ ] Add changelog entry
- [ ] Merge to `main`
