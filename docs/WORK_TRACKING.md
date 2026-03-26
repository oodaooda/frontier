# Work Tracking Guide

This is how we track feature work in Frontier so anyone on the team can pick up, implement, review, and close work in a consistent way.

## The Basic Model

Every feature gets three things:

1. A milestone ID
- Example: `M001`, `M002`
- This is our work-item identifier for the feature.
- It is effectively our internal ticket number.

2. A spec / PRD
- Location: `docs/specs/`
- File pattern: `M###_<slug>_prd.md`
- This explains what we are building and why.

3. A milestone checklist
- Location: `docs/milestones/`
- File pattern: `M###_<slug>_todo.md`
- This explains how the work will be executed and what is still open.

## What Each File Is For

### 1) Spec / PRD
The PRD is the design and scope document.

It should answer:
- What problem are we solving?
- What are the goals?
- What is out of scope?
- What are the functional requirements?
- What are the acceptance criteria?
- What are the risks and mitigations?

Use the PRD when:
- defining the feature
- aligning the team
- reviewing scope
- handing work to another engineer

Example:
- `docs/specs/M001_benchmark-platform_prd.md`

### 2) Milestone Todo
The todo file is the implementation tracker.

It should contain:
- milestone ID
- status
- goal
- link to the PRD
- phased checklist
- manual QA items
- release gate items
- commit checkpoints

Use the todo when:
- implementing the feature
- tracking what is done
- knowing what is blocked
- validating QA
- deciding whether the milestone is ready to merge

Example:
- `docs/milestones/M001_benchmark-platform_todo.md`

### 3) Changelog
Once the milestone is done and signed off, add a changelog entry.

Location:
- `docs/CHANGELOG.md`

This is the record of what actually shipped.

## Branching Convention

Each milestone should have a feature branch.

Pattern:
- `feature/<slug>`

Examples:
- `feature/benchmark-platform`
- `feature/model-runners`

The branch name does not need to include the milestone ID, but it should match the feature clearly.

## Normal Workflow

### Step 1: Create the milestone
Pick the next milestone number.

### Step 2: Write the PRD
Create the spec in `docs/specs/`.

### Step 3: Write the milestone checklist
Create the todo in `docs/milestones/`.

### Step 4: Create the feature branch
```bash
git checkout main
git pull --ff-only origin main
git checkout -b feature/<slug>
```

### Step 5: Implement in phases
Work phase by phase. After each completed phase:
- update the todo checklist
- commit
- push the branch

### Step 6: Validate
Complete automated tests, manual QA, and any rollout checks.

### Step 7: Close the milestone
- mark the PRD and todo status as `complete`
- add the changelog entry
- merge the feature branch into `main`
- push `main`

## Commit Discipline

Commit at meaningful checkpoints, especially after:
- finishing docs/scoping
- finishing a backend phase
- finishing a frontend phase
- finishing tests
- finishing closeout

## What "Done" Means

A milestone is done when:
- the scoped implementation is complete
- the todo checklist is updated
- tests are run
- manual QA is done or explicitly deferred
- the changelog entry is added
- the work is merged to `main`

## How To Split Work Cleanly

If a milestone uncovers a new issue:
- keep the current milestone focused
- document the gap
- create a new milestone for the follow-up work

## Recommended File Naming

Spec: `docs/specs/M###_<slug>_prd.md`
Todo: `docs/milestones/M###_<slug>_todo.md`
Branch: `feature/<slug>`

## Milestone Roadmap

| ID   | Feature                                    | Status  |
|------|--------------------------------------------|---------|
| M001 | Foundation, docs & UI prototypes           | active  |
| M002 | Database layer & document management UI    | planned |
| M003 | Ground truth editor & versioning           | planned |
| M004 | Model runners & evaluation engine          | planned |
| M005 | Scoring, results & comparison dashboard    | planned |
| M006 | Annotations, export & visual testing       | planned |
