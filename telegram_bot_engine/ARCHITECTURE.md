# Telegram Bot Generation Engine — Architecture

This document describes the architecture of the **Telegram Bot Generation
Engine**, a modular system that generates complete Telegram bot projects
from a natural-language description.

The engine is **not a bot**. It is a *factory* that builds bots. Every
file in the generated project is produced by a chain of independent
generation engines, each with a single responsibility.

---

## 1. Design Principles

### 1.1 One Responsibility Per File

No file is responsible for everything. Every module has a single,
clearly defined job. This makes the system testable, maintainable, and
extensible.

### 1.2 No Hardcoded Values

No engine, builder, or validator hardcodes configuration values. All
settings live in the centralised `Configuration` system and are passed
to components at construction time.

### 1.3 No Static Templates

The engine does not copy pre-built projects or use fixed templates.
Every file is generated at run time by a generation engine that reads a
structured blueprint.

### 1.4 Reproducibility

Given the same input and the same engine versions, the engine produces
the same output. Determinism is preserved by sorting, ordered stages,
and explicit metadata.

### 1.5 Independence

Every engine knows nothing about other engines except through the
formal interfaces and the shared `GenerationContext`. Engines communicate
only by reading from and writing to the context.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     User Request                        │
│              "اعمل بوت متجر إلكتروني"                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│                   Pipeline Orchestrator                  │
│   (drives the ordered stages, fail-fast on errors)       │
└──────────────────────┬───────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌───────────┐   ┌──────────┐
   │ Parse   │ → │ Compose   │ → │ Validate │
   │ Stage   │   │ Blueprint  │   │ Blueprint│
   └─────────┘   └───────────┘   └──────────┘
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐   ┌───────────┐   ┌──────────┐   ┌─────────┐
   │Generate │ → │ Validate  │ → │ Package  │ → │ Output  │
   │ Stage   │   │ Output    │   │ Stage    │   │ Manager │
   └─────────┘   └───────────┘   └──────────┘   └─────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │  Generated Bot    │
                                    │  Project (.zip)   │
                                    └──────────────────┘
```

### 2.1 The Two Phases

The pipeline has two logical phases:

1. **Understanding Phase** — the engine parses the user's request into a
   structured *intent*, then composes a *blueprint* from that intent.
   The blueprint is the single contract between understanding and
   building.

2. **Building Phase** — generator engines read the blueprint and
   materialise the project files using builders. Validators check the
   output at each stage.

---

## 3. Layer Breakdown

### 3.1 Configuration (`configuration/`)

Centralised, schema-validated configuration. No engine hardcodes values.

| File | Responsibility |
|------|---------------|
| `schema.py` | Defines the configuration schema (sections, fields, types, defaults). |
| `config.py` | Implements `Configuration` container and `ConfigSource` abstractions (dict, file, environment). |
| `defaults.py` | Assembles the default schema used by the whole engine. |

### 3.2 Logging (`logging/`)

Every step is recorded for traceability.

| File | Responsibility |
|------|---------------|
| `logger.py` | `EngineLogger` facade + `get_logger()` helper. Reads config, configures handlers. |

### 3.3 Blueprint (`blueprint/`)

The intermediate representation of a bot — the contract between the
understanding and building phases.

| File | Responsibility |
|------|---------------|
| `blueprint.py` | All data classes: `Blueprint`, `BotMeta`, `CommandSpec`, `HandlerSpec`, `ConversationSpec`, `DatabaseSpec`, `MiddlewareSpec`, `IntegrationSpec`, `ProjectSpec`. |

### 3.4 Core (`core/`)

The heart of the system. Manages the build lifecycle but contains no
generation logic.

| File | Responsibility |
|------|---------------|
| `contracts.py` | Abstract interfaces: `Engine`, `Builder`, `Validator`, `PipelineStage`, `Component`. |
| `context.py` | `GenerationContext` — the shared state that flows through the pipeline. |
| `result.py` | `StageResult`, `ValidationReport`, `GenerationResult`, `Severity`. |
| `errors.py` | Exception hierarchy. |
| `bootstrap.py` | The single place that wires all components together. |

### 3.5 Registry (`registry/`)

Central catalogue of all components.

| File | Responsibility |
|------|---------------|
| `registry.py` | `EngineRegistry` — maps names to component instances. Dumb container, no logic. |

### 3.6 Engines (`engines/`)

All generation engines. Each engine has a single responsibility.

| File | Responsibility |
|------|---------------|
| `base/base_engine.py` | Shared boilerplate for engines (logger, result helpers). |
| `base/base_generator.py` | Shared boilerplate for generators (builder references, file helpers). |
| `generators/intent_parser_engine.py` | Parses a natural-language request into a structured intent. |
| `generators/blueprint_composer_engine.py` | Composes a blueprint from an intent using bot-type profiles. |

### 3.7 Builders (`builders/`)

The **only** components that write files to disk.

| File | Responsibility |
|------|---------------|
| `directory_builder.py` | Creates directory structures. |
| `file_builder.py` | Writes individual files. |
| `python_module_builder.py` | Writes Python modules with a standardised header. |

### 3.8 Validators (`validators/`)

Verify artefacts at each stage.

| File | Responsibility |
|------|---------------|
| `base_validator.py` | Shared boilerplate for validators. |
| `blueprint_validator.py` | Validates blueprint consistency (applies to "blueprint"). |
| `structure_validator.py` | Validates generated file structure and Python syntax (applies to "output"). |

### 3.9 Pipeline (`pipeline/`)

The ordered path a request follows.

| File | Responsibility |
|------|---------------|
| `base_stage.py` | Shared boilerplate for stages (logging, error handling, preconditions). |
| `orchestrator.py` | Drives the full pipeline. The only place that knows stage order. |
| `stages/parse_stage.py` | Parses the request. |
| `stages/compose_blueprint_stage.py` | Composes the blueprint. |
| `stages/validate_blueprint_stage.py` | Validates the blueprint. |
| `stages/generate_stage.py` | Runs all generator engines. |
| `stages/validate_output_stage.py` | Validates the generated output. |
| `stages/package_stage.py` | Packages the final deliverable. |

### 3.10 Output (`output/`)

Assembles and packages the final deliverable after validation.

| File | Responsibility |
|------|---------------|
| `output_manager.py` | Finalises the project directory, creates zip archive, returns `PackageInfo`. |

---

## 4. The Generation Flow

### 4.1 Step by Step

1. **User calls `generate_bot("description")`**.
2. **Bootstrap** assembles the registry, builders, engines, validators,
   and the orchestrator.
3. **Orchestrator** creates a `GenerationContext` with the request.
4. **Parse Stage** — the intent parser engine converts the request into a
   structured `intent` dictionary.
5. **Compose Blueprint Stage** — the blueprint composer engine builds a
   `Blueprint` from the intent using bot-type profiles.
6. **Validate Blueprint Stage** — the blueprint validator checks the
   blueprint for consistency.
7. **Generate Stage** — each generator engine reads the blueprint and
   uses builders to write files to the work directory.
8. **Validate Output Stage** — the structure validator checks the
   generated files (existence, syntax, structure).
9. **Package Stage** — the output manager finalises the project,
   creates a zip, and returns `PackageInfo`.
10. **Result** — a `GenerationResult` with the project path and
    metadata is returned.

### 4.2 Fail-Fast Semantics

By default, the pipeline stops at the first failing stage. This
behaviour is configurable via `pipeline.fail_fast` in the configuration.

---

## 5. Extension Points

### 5.1 Adding a New Generator Engine

1. Create a new file in `engines/generators/` (e.g.
   `handler_generator_engine.py`).
2. Implement a class inheriting from `BaseGenerator`.
3. Register the engine in `core/bootstrap.py`.
4. No other file changes — the pipeline automatically picks it up.

### 5.2 Adding a New Bot Type Profile

1. Add a profile function in `blueprint_composer_engine.py`.
2. Add an entry to the `_PROFILES` dispatch table.
3. No other file changes.

### 5.3 Adding a New Validator

1. Create a new file in `validators/` inheriting from `BaseValidator`.
2. Set `applies_to` metadata to `"blueprint"` or `"output"`.
3. Register in `core/bootstrap.py`.

### 5.4 Adding a New Builder

1. Create a new file in `builders/` inheriting from `Builder`.
2. Register in `core/bootstrap.py`.

### 5.5 Adding a New Configuration Option

1. Add a `FieldSchema` to the appropriate section in
   `configuration/defaults.py`.
2. Read it in the component that needs it via `config.get()`.

---

## 6. Current Status

### Implemented

- ✅ Configuration system (schema, sources, validation).
- ✅ Logging system.
- ✅ Blueprint data model.
- ✅ Core contracts and context.
- ✅ Engine registry.
- ✅ Builders (directory, file, python module).
- ✅ Understanding engines (intent parser, blueprint composer).
- ✅ Validators (blueprint, structure).
- ✅ Pipeline stages (all six stages).
- ✅ Pipeline orchestrator.
- ✅ Output manager.
- ✅ Bootstrap wiring.
- ✅ High-level `generate_bot()` entry point.

### To Be Implemented (Future Phases)

- ⬜ Project Scaffolding Generator (creates folder structure + `__init__.py` files).
- ⬜ Bot Core Generator (writes `main.py` — the bot entry point).
- ⬜ Handler Generator (writes command and message handlers).
- ⬜ Conversation/State Machine Generator (writes conversation handlers).
- ⬜ Database Layer Generator (writes database models and session).
- ⬜ Middleware Generator (writes middleware components).
- ⬜ Config Generator (writes `config.py` and `.env.example`).
- ⬜ Requirements Generator (writes `requirements.txt`).
- ⬜ Deployment Generator (writes `Dockerfile`, `docker-compose.yml`).
- ⬜ README Generator (writes project documentation).
- ⬜ Engine auto-discovery (scan packages for registered engines).
- ⬜ CLI entry point.

---

## 7. Directory Structure

```
telegram_bot_engine/
├── __init__.py                      # High-level entry point
├── blueprint/
│   ├── __init__.py
│   └── blueprint.py                  # Data model
├ builders/
│   ├── __init__.py
│   ├── directory_builder.py
│   ├── file_builder.py
│   └── python_module_builder.py
├── configuration/
│   ├── __init__.py
│   ├── config.py
│   ├── defaults.py
│   └── schema.py
├── core/
│   ├── __init__.py
│   ├── bootstrap.py
│   ├── configuration.py              # [planned]
│   ├── contracts.py
│   ├── context.py
│   ├── errors.py
│   └── result.py
├── engines/
│   ├── __init__.py
│   ├── base/
│   │   ├── __init__.py
│   │   ├── base_engine.py
│   │   └── base_generator.py
│   └── generators/
│       ├── __init__.py
│       ├── blueprint_composer_engine.py
│       └── intent_parser_engine.py
├── logging/
│   ├── __init__.py
│   └── logger.py
├── output/
│   ├── __init__.py
│   └── output_manager.py
├── pipeline/
│   ├── __init__.py
│   ├── base_stage.py
│   ├── orchestrator.py
│   └── stages/
│       ├── __init__.py
│       ├── compose_blueprint_stage.py
│       ├── generate_stage.py
│       ├── package_stage.py
│       ├── parse_stage.py
│       ├── validate_blueprint_stage.py
│       └── validate_output_stage.py
├── registry/
│   ├── __init__.py
│   └── registry.py
└── validators/
    ├── __init__.py
    ├── base_validator.py
    ├── blueprint_validator.py
    └── structure_validator.py
```
