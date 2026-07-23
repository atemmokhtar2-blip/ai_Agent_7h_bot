# AI Agent 7h Bot — Telegram Bot Generation Engine

## Project Overview

A modular Python engine that generates complete Telegram bot projects from a natural-language description. The engine is not a bot itself — it is a factory that builds bots.

**Stack:** Python 3.12, no external dependencies.

**Current status:** Specifications 001–004 are complete and fully tested (341 tests passing). Specification 005 is next.

## How to Run Tests

Use the **Run Tests** workflow, or run from the shell:

```bash
PYTHONPATH=. python tests/test_manager.py
PYTHONPATH=. python tests/test_project_planner.py
```

Expected output: `53 passed, 0 failed` and `288 passed, 0 failed`.

## Architecture

```
telegram_bot_engine/
├── configuration/       # Schema-validated configuration
├── logging/             # Structured logging
├── blueprint/           # Intermediate bot representation
├── core/                # Bootstrap, contracts, context, errors, results
├── registry/            # Component registry
├── manager/             # Engine lifecycle manager (Spec 003)
├── engines/
│   ├── base/            # BaseEngine class
│   └── generators/
│       ├── analyzer/    # Request analyzer (Spec 002) — 10 stages
│       └── project_planner/  # Project planner (Spec 004) — 8 phases
├── builders/            # File/directory writers
├── validators/          # Blueprint and structure validators
├── pipeline/            # 6-stage pipeline orchestrator
└── output/              # Output manager (packages the final deliverable)
```

## Development Convention

This project is built via numbered specifications (001, 002, …). Each specification is implemented completely and tested before the next begins. **Do not add components outside a specification's scope.**

## User Preferences

- Arabic is the primary language for README and comments; English for code.
