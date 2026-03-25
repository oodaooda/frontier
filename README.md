# Frontier

Benchmark suite for evaluating AI model capabilities on construction document understanding.

## Overview

Frontier tests how well vision-capable AI models can read and interpret construction documents — drawings, specifications, schedules, tables, and project lookaheads. Run the same test suite against new models as they release to track capability improvements over time.

## Task Tiers

| Tier | Type | Example |
|------|------|---------|
| 1 | Text extraction | Pull values from tables, schedules, spec sections |
| 2 | Structured understanding | Interpret relationships between document elements |
| 3 | Spatial/visual reasoning | Read dimensions from drawings, identify plan elements |

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Render PDFs to images
frontier render datasets/pdfs/A-301.pdf

# Run evaluation
frontier run -m claude-opus-4-6 -m gpt-5.4

# Generate comparison report
frontier report reports/results/
```

## Project Structure

```
frontier/
├── config.yaml                  # Benchmark configuration
├── datasets/
│   ├── pdfs/                    # Source PDF documents
│   ├── ground_truth/            # Question/answer pairs (YAML)
│   └── rendered/                # Rendered page images (generated)
├── prompts/                     # Prompt templates
├── reports/                     # Generated evaluation reports
├── src/frontier/
│   ├── cli.py                   # CLI entry point
│   ├── runners/                 # Model API adapters
│   ├── scorers/                 # Answer evaluation logic
│   ├── reporters/               # Report generation
│   └── utils/                   # PDF rendering, helpers
└── tests/                       # Test suite
```

## Adding a New Model

1. Create a runner in `src/frontier/runners/` extending `BaseRunner`
2. Add the model config to `config.yaml`
3. Run `frontier run -m <model-id>`

## Ground Truth Format

See `datasets/ground_truth/_schema.yaml` for the full schema. Each YAML file contains tasks tied to a specific PDF document.
