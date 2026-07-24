# Telegram Bot Generation Engine
## Complete Technical Documentation — All 12 Engines

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Core Infrastructure](#3-core-infrastructure)
4. [Engine 01 — Core Request Analyzer Engine](#4-engine-01--core-request-analyzer-engine)
5. [Engine 02 — Intent Parser Engine](#5-engine-02--intent-parser-engine)
6. [Engine 03 — Blueprint Composer Engine](#6-engine-03--blueprint-composer-engine)
7. [Engine 04 — Project Planning Engine](#7-engine-04--project-planning-engine)
8. [Engine 05 — Blueprint Validator Engine](#8-engine-05--blueprint-validator-engine)
9. [Engine 06 — Structure Generation Engine](#9-engine-06--structure-generation-engine)
10. [Engine 07 — Component Detection Engine](#10-engine-07--component-detection-engine)
11. [Engine 08 — File Generation Planning Engine](#11-engine-08--file-generation-planning-engine)
12. [Engine 09 — Visual Page Reconstruction Engine](#12-engine-09--visual-page-reconstruction-engine)
13. [Engine 09b — Dependency Resolution Engine](#13-engine-09b--dependency-resolution-engine)
14. [Engine 10 — Project Context Engine](#14-engine-10--project-context-engine)
15. [Engine 11 — Project Intelligence Graph Engine](#15-engine-11--project-intelligence-graph-engine)
16. [Pipeline Architecture & Data Flow](#16-pipeline-architecture--data-flow)
17. [Core Engine Manager](#17-core-engine-manager)
18. [Test Suite Summary](#18-test-suite-summary)
19. [Technology Stack](#19-technology-stack)
20. [Design Principles](#20-design-principles)
21. [Project Statistics](#21-project-statistics)

---

## 1. System Overview

The **Telegram Bot Generation Engine** is a modular, pipeline-based system that takes a natural-language description of a desired Telegram bot from a user and produces a complete, ready-to-run Python project. The system is built around the principle that understanding, planning, validation, and generation are fundamentally different responsibilities that must be performed by separate, specialized engines — each with a clearly defined contract, a specific set of inputs, a single output, and no ability to do anything outside its designated scope.

The system is organized as a linear pipeline where each stage reads the outputs (called **artefacts**) of previous stages, performs its specialized work, and writes its own output artefact into a shared **GenerationContext**. No engine ever reads the raw user request directly (except the first two in the understanding phase). No engine ever communicates with another engine directly — all communication flows through the GenerationContext and the Core Engine Manager.

The system is composed of **12 engines** spanning four phases of the build lifecycle:

**Phase 1 — Understanding (Engines 1–3):** The system reads the user's natural-language request, analyses it deeply, parses it into a structured intent, and composes a preliminary blueprint.

**Phase 2 — Planning (Engines 4–5):** The system converts the analysis report into a professional Project Blueprint with a full execution plan, then validates that blueprint through six independent layers.

**Phase 3 — Generation Planning (Engines 6–11):** The system builds the physical structure map, detects all components, plans all files, resolves all dependencies, merges everything into a unified Project Context, and converts all of it into a single Project Intelligence Graph with O(1) look-up indices — all before any file is created on disk or any line of code is written.

**Phase 4 — Visual Reconstruction (Engine 9):** A specialized engine that reads PDF files and reconstructs their pages with pixel-accurate visual fidelity.

The total codebase comprises **151 Python source files** totalling **36,404 lines of code**, supported by **9 test files** totalling **16,840 lines** of comprehensive test coverage.

---

## 2. Architecture

### 2.1 Pipeline Architecture

The system uses a **linear pipeline with artefact-based communication**. Each engine in the pipeline:

1. Reads one or more artefacts from the `GenerationContext.artefacts` dictionary.
2. Performs its specialized work (analysis, planning, validation, or generation).
3. Writes its output artefact back into the same dictionary.
4. Returns a `StageResult` indicating success or failure with detailed metadata.

The pipeline is **fail-fast**: if any engine fails, the entire pipeline stops. No downstream engine is allowed to run if an upstream engine has not completed successfully.

### 2.2 Engine Contract Pattern

Every engine inherits from `BaseEngine`, which inherits from `Engine(ABC, Component)`:

```
Component (dataclass: name, version, description, tags, metadata)
    └── Engine (ABC, adds: execute(context) -> StageResult)
            └── BaseEngine (adds: logger, ok() helper, failed() helper)
                    └── Concrete Engine (implements: execute())
```

The `BaseEngine` class provides:
- A logger (`self._log`) accessible as `get_logger(f"engine.{name}")`.
- An `ok()` helper that returns a successful `StageResult`.
- A `failed()` helper that returns a failed `StageResult` with errors and warnings.
- The abstract `execute()` method that every concrete engine must implement.

### 2.3 GenerationContext

The `GenerationContext` is the sole vehicle for state transfer between engines. It is a dataclass containing:

- `request: str` — the user's original natural-language request.
- `config: Configuration` — the engine configuration.
- `work_dir: Path` — the working directory for file output.
- `run_id: str` — a unique identifier for this generation run.
- `blueprint: Optional[Blueprint]` — the legacy blueprint (used by the old pipeline).
- `artefacts: Dict[str, Any]` — the primary communication channel between engines.
- `metadata: Dict[str, Any]` — supplementary metadata.
- `created_files: list` — tracking of all files created during generation.

The context provides helper methods:
- `set(key, value)` — store an artefact.
- `get(key, default=None)` — retrieve an artefact.
- `has(key)` — check whether an artefact exists.
- `track_file(path)` — record a created file.

### 2.4 StageResult

Every engine's `execute()` method returns a `StageResult` — a dataclass containing:

- `stage_name: str` — the name of the engine that produced the result.
- `success: bool` — whether the stage completed without errors.
- `outputs: Dict[str, Any]` — artefacts produced by the stage.
- `errors: List[str]` — error messages (causes pipeline to stop).
- `warnings: List[str]` — warning messages (do not stop the pipeline).
- `metadata: Dict[str, Any]` — diagnostic information.

The `StageResult` class provides two factory methods:
- `StageResult.ok(stage_name, outputs, metadata, warnings)` — create a successful result.
- `StageResult.failed(stage_name, errors, outputs, warnings, metadata)` — create a failed result.

### 2.5 Engine Registration and Ordering

Engines are registered in two places:

1. **EngineRegistry** — a "dumb catalogue" that stores engine instances, builders, and validators. It provides lookup by name but enforces no policy.

2. **CoreEngineManager** — the "executive brain" that governs every engine's lifecycle, dependencies, execution order, and error handling. It registers engines with a unique ID, a priority number, and a list of dependencies. The manager uses topological sorting to determine the correct execution order and enforces that no engine runs until all its dependencies have completed successfully.

The registration in `bootstrap.py` assigns each engine a priority number (lower = earlier in the pipeline) and a list of dependency engine IDs that must complete before this engine can run.

---

## 3. Core Infrastructure

### 3.1 File Inventory

The core infrastructure consists of the following modules:

| Module | Path | Responsibility |
|--------|------|----------------|
| `contracts.py` | `telegram_bot_engine/core/contracts.py` | Abstract interfaces: `Component`, `Engine`, `Builder`, `PipelineStage` |
| `context.py` | `telegram_bot_engine/core/context.py` | `GenerationContext` — shared state container |
| `result.py` | `telegram_bot_engine/core/result.py` | `StageResult`, `ValidationReport`, `Severity` |
| `errors.py` | `telegram_bot_engine/core/errors.py` | `ConfigurationError` and related exceptions |
| `bootstrap.py` | `telegram_bot_engine/core/bootstrap.py` | System assembly — the only place that knows concrete engines |
| `engine_manager.py` | `telegram_bot_engine/manager/engine_manager.py` | `CoreEngineManager` — lifecycle, dependencies, security |
| `engine_entry.py` | `telegram_bot_engine/manager/engine_entry.py` | `EngineEntry`, `EngineMetadata` — managed engine records |
| `execution_queue.py` | `telegram_bot_engine/manager/execution_queue.py` | `ExecutionQueue`, `QueueItem` — execution ordering |
| `lifecycle.py` | `telegram_bot_engine/manager/lifecycle.py` | `EngineState`, `EngineStateTransition` — lifecycle states |
| `orchestrator.py` | `telegram_bot_engine/pipeline/orchestrator.py` | `PipelineOrchestrator` — drives the full pipeline |
| `registry.py` | `telegram_bot_engine/registry/registry.py` | `EngineRegistry` — dumb catalogue |

### 3.2 Component Contract

```python
@dataclass
class Component:
    name: str
    version: str = "1.0.0"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

Every engine, builder, and validator is a `Component`. The `name` must be non-empty (enforced in `__post_init__`).

### 3.3 Engine Contract

```python
class Engine(ABC, Component):
    @abstractmethod
    def execute(self, context: GenerationContext) -> StageResult:
        ...
```

The `execute()` method is the sole entry point for every engine. It receives a `GenerationContext` and returns a `StageResult`.

### 3.4 BaseEngine

```python
class BaseEngine(Engine):
    def __init__(self, name, version="1.0.0", description="",
                 tags=None, metadata=None) -> None:
        ...
        self._log = get_logger(f"engine.{name}")

    def ok(self, outputs=None, metadata=None) -> StageResult:
        return StageResult.ok(self.name, outputs=outputs, metadata=metadata)

    def failed(self, errors, outputs=None, warnings=None) -> StageResult:
        return StageResult.failed(self.name, errors=errors,
                                    outputs=outputs, warnings=warnings)

    def execute(self, context):
        raise NotImplementedError(...)
```

---

## 4. Engine 01 — Core Request Analyzer Engine

### 4.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `analyzer` |
| **Priority** | 10 |
| **Dependencies** | `[]` (none — first engine in the pipeline) |
| **Version** | `2.0.0` |
| **Tags** | `["understanding", "analysis"]` |
| **Phase** | `understanding` |
| **Stage Count** | 10 |
| **Source Files** | 14 files, 2,642 lines |
| **Output Artefact** | `analysis_report` (type: `AnalysisReport`) |
| **Input** | The user's raw request from `context.request` |

The **Core Request Analyzer Engine** is the first engine in the pipeline and the only engine (besides the Intent Parser) that reads the user's raw natural-language request. It performs a comprehensive 10-stage analysis and produces an `AnalysisReport` — the single, authoritative description of what the user wants. The analysis is **pure**: no code is generated, no files are created, no structures are built.

### 4.2 The 10 Analysis Stages

The engine runs 10 stages sequentially, each stage receiving a shared mutable state dictionary and the `AnalysisReport` object:

| Stage | Name | File | Responsibility |
|-------|------|------|----------------|
| 1 | `cleaner` | `stage1_cleaner.py` | Normalise whitespace, remove noise from the raw text. |
| 2 | `segmenter` | `stage2_segmenter.py` | Sentence segmentation, tokenisation, language detection. |
| 3 | `keyword_extractor` | `stage3_keyword_extractor.py` | Category-tagged keyword matching. |
| 4 | `classifier` | `stage4_classifier.py` | Bot type detection and ordering. |
| 5 | `feature_extractor` | `stage5_feature_extractor.py` | Independent, atomic feature extraction. |
| 6 | `technology_extractor` | `stage6_technology_extractor.py` | Languages, libraries, databases, frameworks detection. |
| 7 | `relationship_analyzer` | `stage7_relationship_analyzer.py` | Dependencies between entities. |
| 8 | `conflict_detector` | `stage8_conflict_detector.py` | Contradictory or ambiguous choices. |
| 9 | `missing_info_detector` | `stage9_missing_info_detector.py` | Questions for the user (missing information). |
| 10 | `report_builder` | `stage10_report_builder.py` | Confidence scores and readiness assessment. |

### 4.3 Data Model (AnalysisReport)

The `AnalysisReport` class contains the following data classes:

- `Token` — a single token with its position and type.
- `KeywordMatch` — a matched keyword with its category.
- `BotTypeEntry` — a detected bot type with confidence score.
- `Feature` — an independent, atomic feature with display name, description, related entities, related features, keywords, and confidence.
- `Technology` — a detected technology with category (language, library, database, framework, external_api).
- `Relationship` — a relationship between entities (source, target, kind, description).
- `Conflict` — a detected conflict between features or technologies.
- `MissingInfo` — a missing piece of information with a question for the user.
- `ConfidenceScore` — a confidence score for the analysis.
- `AnalysisReport` — the complete report containing all the above.

### 4.4 Key Properties

The `AnalysisReport` provides:
- `primary_bot_type` — the highest-confidence bot type.
- `features` — the list of detected features.
- `technologies` — the list of detected technologies.
- `conflicts` — the list of detected conflicts.
- `missing_info` — the list of missing information items.
- `has_conflicts` — whether any conflicts were detected.
- `has_missing_required_info` — whether any required info is missing.
- `ready` — whether the analysis is complete and ready for the next stage.
- `project_name` — the determined project name.
- `cleaned_request` — the cleaned request text.
- `notes` and `warnings` — supplementary information.

### 4.5 Execution Flow

```
raw_request → [Stage 1: Clean] → [Stage 2: Segment] → [Stage 3: Keywords]
→ [Stage 4: Classify] → [Stage 5: Features] → [Stage 6: Technologies]
→ [Stage 7: Relationships] → [Stage 8: Conflicts] → [Stage 9: Missing Info]
→ [Stage 10: Report] → AnalysisReport → context.artefacts["analysis_report"]
```

If any stage throws an exception, the engine immediately fails with an error message identifying the failing stage. All warnings from all stages are accumulated and returned in the final `StageResult`.

### 4.6 Output

The engine stores the `AnalysisReport` in:
- `context.artefacts["analysis_report"]`
- `context.metadata["analysis_report"]`

The `StageResult.outputs` dictionary contains:
- `analysis_report` — the full report.
- `bot_type` — the primary bot type string.
- `features` — list of feature names.
- `technologies` — list of technology names.
- `ready` — the readiness flag.

---

## 5. Engine 02 — Intent Parser Engine

### 5.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `intent_parser` |
| **Priority** | 20 |
| **Dependencies** | `["analyzer"]` |
| **Version** | `1.0.0` |
| **Tags** | `["understanding"]` |
| **Phase** | `understanding` |
| **Source Files** | 1 file, 121 lines |
| **Output Artefact** | `intent` (type: `Dict`) |
| **Input** | The user's raw request from `context.request` |

The **Intent Parser Engine** converts the user's natural-language request into a structured intent dictionary. It is the second engine in the pipeline and the last engine that reads the raw request directly. The current implementation uses a **rule-based heuristic** — a set of keyword-matching rules that classify the bot type and detect features. The design allows this engine to be replaced with an LLM-backed implementation in the future without affecting any downstream component, because they all rely on the `intent` artefact shape, not on this engine's internals.

### 5.2 Bot Type Classification Rules

The engine uses 10 bot-type classification rules, each mapping a list of keywords (matched case-insensitively) to a bot type identifier. The first matching rule wins:

| Bot Type | Keywords (English + Arabic) |
|----------|------------------------------|
| `group_admin` | group, admin, manage, moderat, إدارة, إدارة |
| `store` | store, shop, ecommerce, متجر, متجري |
| `downloader` | download, downloader, تحميل, يوتيوب, youtube, video, فيديو |
| `ai_assistant` | ai, gpt, chatgpt, ذكاء, اصطناعي |
| `task_manager` | todo, task, reminder, مهمة, مهام |
| `quiz` | quiz, poll, survey, استبيان |
| `news` | news, rss, اخبار, أخبار |
| `weather` | weather, طقس |
| `currency` | currency, price, اسعار, أسعار |
| `assistant` | chat, assistant, helper, مساعد |

If no rule matches, the bot type defaults to `"general"`.

### 5.3 Feature Detection

The engine detects features using a `feature_map` that maps feature names to lists of keywords:

- `database` — database, db, store data, قاعدة, بيانات
- `admin_panel` — admin, panel, لوحة, تحكم
- `payments` — payment, pay, checkout, دفع, مدفوعات
- `ai` — ai, gpt, ذكاء, اصطناعي
- `media_download` — download, youtube, تحميل, فيديو
- `scheduling` — schedule, cron, جدولة, مجدول
- `multi_language` — language, multilingual, لغات, متعدد
- `rate_limit` — rate, limit, حد, محدود
- `logging` — log, logging, سجل, تسجيل

### 5.4 Language Detection

The engine detects whether the request contains Arabic characters using the regex `[\u0600-\u06FF]`. If it matches, the language is `"ar"`; otherwise it is `"en"`.

### 5.5 Output

The intent dictionary contains:
- `raw` — the original request text.
- `bot_type` — the classified bot type.
- `features` — the list of detected feature names.
- `language` — the detected language (`"ar"` or `"en"`).
- `language_version` — always `"3.11"`.
- `framework` — always `"python-telegram-bot"`.

---

## 6. Engine 03 — Blueprint Composer Engine

### 6.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `blueprint_composer` |
| **Priority** | 30 |
| **Dependencies** | `["analyzer", "intent_parser"]` |
| **Version** | `1.0.0` |
| **Tags** | `["understanding"]` |
| **Phase** | `understanding` |
| **Source Files** | 1 file, 327 lines |
| **Output Artefact** | `blueprint` (type: `Blueprint`) |
| **Input** | `intent` artefact from the Intent Parser Engine |

The **Blueprint Composer Engine** assembles a complete `Blueprint` from the parsed intent using **bot-type profiles**. Each profile is a function that returns the blueprint pieces specific to that bot type: default commands, handlers, conversations, middlewares, database models, and integrations. Profiles are plain data, so new bot types can be added by adding a new function and a new entry in the dispatch table — no existing code changes.

### 6.2 Bot-Type Profiles

The engine has 5 profiles:

**1. `_group_admin_profile`** — Group administration bot:
- Commands: start, help, ban, mute, warn, settings (admin-only)
- Handlers: new_members, spam_filter
- Middlewares: spam_filter, rate_limiter
- Database: GroupSettings model, Warn model (SQLite)

**2. `_store_profile`** — E-commerce store bot:
- Commands: start, help, products, cart, order, myorders
- Conversations: checkout (entry_command="order", states: ask_name → ask_address → ask_phone → confirm)
- Database: Product model, Order model (SQLite)
- Integrations: payment (with PAYMENT_API_KEY env var)

**3. `_downloader_profile`** — Media downloader bot:
- Commands: start, help, download (with url argument)
- Handlers: url_handler
- Integrations: yt_dlp

**4. `_ai_assistant_profile`** — AI assistant bot:
- Commands: start, help, ask (with query), clear, setmodel (admin-only)
- Integrations: openai (with OPENAI_API_KEY, AI_MODEL env vars)
- Database: Conversation model (SQLite)

**5. `_general_profile`** — General purpose bot:
- Commands: start, help only

### 6.3 Arabic Slugification

The engine includes a `_slugify()` function that converts text into a valid Python package name. Arabic text is transliterated to a meaningful English slug using a keyword map (e.g., "متجر" → "store", "تحميل" → "downloader", "ذكاء" → "ai"). Remaining non-ASCII characters are replaced with underscores, and multiple underscores are collapsed into one.

### 6.4 Default Dependencies

The engine computes default dependencies based on bot type and detected features:

- Always: `python-telegram-bot>=20.7`
- If database feature or bot type in (store, group_admin, ai_assistant): `SQLAlchemy>=2.0`
- If AI feature or bot type is ai_assistant: `openai>=1.0`
- If media_download feature or bot type is downloader: `yt-dlp`
- If payments feature: `stripe`

### 6.5 Output

The engine produces a `Blueprint` object (from `telegram_bot_engine.blueprint`) containing:
- `meta: BotMeta` — name, display_name, description, bot_type
- `project: ProjectSpec` — name, description, python_version, dependencies
- `commands: List[CommandSpec]`
- `handlers: List[HandlerSpec]`
- `conversations: List[ConversationSpec]`
- `database: DatabaseSpec`
- `middlewares: List[MiddlewareSpec]`
- `integrations: List[IntegrationSpec]`
- `extra: Dict` — contains features list

---

## 7. Engine 04 — Project Planning Engine

### 7.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `project_planner` |
| **Priority** | 40 |
| **Dependencies** | `["analyzer"]` |
| **Version** | `1.0.0` |
| **Tags** | `["planning"]` |
| **Phase** | `planning` |
| **Source Files** | 8 files, 2,405 lines |
| **Output Artefact** | `project_blueprint` (type: `ProjectBlueprint`) |
| **Input** | `analysis_report` artefact from the Analyzer Engine |

The **Project Planning Engine** is the planning brain of the system. It does **not** generate code, create files, or build folders. Its sole function is to convert the `AnalysisReport` into a professional, clear build plan — the `ProjectBlueprint` — that the rest of the system relies on. The engine is **forbidden** from reading the user's request directly; it reads only the `analysis_report` artefact.

### 7.2 Internal Steps

The engine builds the blueprint in 10 internal steps:

**Step 1 — Project Identity:** Determines the project name, display name, bot type, language (Python), language version (3.11), framework (python-telegram-bot), libraries, and database. Uses `_slugify()` for the package name.

**Step 2 — Expected Structure:** Builds the expected folder/file layout using `_common_structure()` which creates a root package directory with `__init__.py`, `config.py`, `main.py`, `handlers/`, `models/`, `requirements.txt`, `.env.example`, and `README.md`.

**Step 3 — Feature Breakdown:** Converts each `Feature` from the analysis report into a `FeatureUnit` with a build priority (critical, high, normal, low), a phase assignment, component introductions, and dependency hints.

**Step 4 — Internal Components:** Builds the `InternalComponent` list. Always includes `config_loader` (critical priority) and `logger` (high priority) as infrastructure. Adds a `database` component if any feature needs it. Adds a component for each feature unit.

**Step 5 — Component Relationships:** Builds `ComponentRelationship` edges from component dependencies, analysis report relationships, and feature-to-feature dependencies.

**Step 6 — Dependency Graph:** Builds a `DependencyGraph` with all components and features as nodes and their dependencies as edges. The graph provides `parallel_groups()` for parallel execution planning.

**Step 7 — Required Engines:** Determines the set of required generator engines for the 8 execution phases: project_setup_engine, structure_builder_engine, database_engine (conditional), file_builder_engine, code_generator_engine, wiring_engine, review_engine, export_engine.

**Step 8 — Execution Plan:** Builds the `ExecutionPlan` with 8 fixed phases (see section 7.3 below). Assigns engines, components, and features to their appropriate phases. Computes the parallel design summary.

**Step 9 — Risk Detection:** Uses `RiskDetector` to detect conflicts, missing information, missing phases, and incomplete dependencies. Each `BlueprintRisk` has a severity, kind, description, affected element, and resolution hint.

**Step 10 — Validation:** Uses `BlueprintValidator` to perform three required checks on the feature units, dependency graph, and execution plan. The `BlueprintValidation` result contains `valid`, `errors`, and `warnings`.

### 7.3 The Eight Execution Phases

The execution plan divides the project into 8 ordered phases (mandated by the specification, order may not be changed unless the planning engine proves it is safe):

| Phase | Name | Description | Can Parallel | Skippable |
|-------|------|-------------|-------------|-----------|
| 1 | `project_setup` | Initialise the project, configuration, and environment. | No | No |
| 2 | `create_structure` | Create the folder and file structure. | Yes | No |
| 3 | `build_database` | Build database models and schema. | Yes | Yes |
| 4 | `create_files` | Create source files for each component. | Yes | No |
| 5 | `generate_code` | Generate implementation code for each component. | Yes | No |
| 6 | `wire_components` | Wire components together and connect dependencies. | No | No |
| 7 | `review` | Review the generated project for correctness. | Yes | No |
| 8 | `export` | Export the final, packaged project. | No | No |

Each `ExecutionPhase` carries: number, name, description, status (pending/in_progress/completed/skipped/blocked), engines, components, features, can_parallel, and skippable flags.

### 7.4 Data Model (ProjectBlueprint)

The `ProjectBlueprint` class (from `blueprint.py`) contains:

- `ProjectIdentity` — name, display_name, bot_type, language, language_version, framework, libraries, database.
- `ExpectedStructure` — root and entries (list of `StructureEntry`).
- `StructureEntry` — path, kind (directory/file), description.
- `FeatureUnit` — name, display_name, description, source_feature, build_priority, phase, introduces_components, depends_on_components, depends_on_features, parallel_safe, requires_database, requires_config, confidence, metadata.
- `InternalComponent` — name, display_name, kind (infrastructure/feature/integration), priority, description, source_feature, dependencies.
- `ComponentRelationship` — source, target, kind, description.
- `DependencyGraph` — nodes and edges with parallel_groups() method.
- `RequiredEngine` — engine_id, name, purpose, phase, priority.
- `ExecutionPlan` — phases (list of `ExecutionPhase`), parallel_design, order_locked.
- `BlueprintRisk` — severity, kind, description, affected, resolution_hint.
- `BlueprintValidation` — valid, errors, warnings.
- `ProjectBlueprint` — the complete blueprint containing all the above.

### 7.5 Sub-Modules

| File | Lines | Responsibility |
|------|-------|----------------|
| `planning_engine.py` | ~530 | Main engine class with 10 internal steps |
| `blueprint.py` | ~380 | All data classes for the blueprint |
| `execution_plan.py` | ~200 | ExecutionPlan, ExecutionPhase, PhaseStatus, DEFAULT_PHASES |
| `feature_unit.py` | ~150 | FeatureUnit with priority constants |
| `dependency_graph.py` | ~200 | DependencyGraph with parallel_groups() |
| `risk_detection.py` | ~200 | RiskDetector |
| `validation.py` | ~150 | BlueprintValidator |

### 7.6 Priority Constants

```python
PRIORITY_CRITICAL = 1
PRIORITY_HIGH = 2
PRIORITY_NORMAL = 3
PRIORITY_LOW = 4
```

### 7.7 Output

The engine stores the `ProjectBlueprint` in:
- `context.artefacts["project_blueprint"]`
- `context.metadata["project_blueprint"]`

The blueprint's `ready` flag is set to `True` only if the internal validation passed. If validation fails, the engine returns a `failed` result with all error messages.

---

## 8. Engine 05 — Blueprint Validator Engine

### 8.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `blueprint_validator` |
| **Priority** | 50 |
| **Dependencies** | `["project_planner"]` |
| **Version** | `1.0.0` |
| **Tags** | `["validation", "blueprint"]` |
| **Phase** | `validation` |
| **Source Files** | 12 files, 2,494 lines |
| **Output Artefact** | `blueprint_validation_report` (type: `BlueprintValidationReport`) |
| **Input** | `project_blueprint` artefact from the Project Planning Engine |

The **Blueprint Validator Engine** is the gatekeeper that decides whether a `ProjectBlueprint` may proceed to the building phase. It does **not** generate code, create files, or modify the blueprint. Its sole function is to validate the blueprint through **six independent layers**, detect conflicts, compute a quality score, and produce an authoritative **APPROVED** or **REJECTED** verdict. No generation engine may proceed until this report's `status` is `APPROVED`.

### 8.2 The Six Validation Layers

The engine runs six independent validation layers in order:

| Layer | Name | File | Responsibility |
|-------|------|------|----------------|
| 1 | `layer1_basic_data` | `layer1_basic_data.py` | Validate basic project data (name, type, language, framework). |
| 2 | `layer2_features` | `layer2_features.py` | Validate all features are complete and non-contradictory. |
| 3 | `layer3_relationships` | `layer3_relationships.py` | Validate all component relationships are valid. |
| 4 | `layer4_execution_plan` | `layer4_execution_plan.py` | Validate the execution plan phases and assignments. |
| 5 | `layer5_dependencies` | `layer5_dependencies.py` | Validate all declared dependencies are consistent. |
| 6 | `layer6_buildability` | `layer6_buildability.py` | Validate the overall buildability of the project. |

Each layer returns a `LayerResult` containing:
- `name` — the layer name.
- `passed` — whether the layer passed.
- `errors` — list of `ValidationFinding` objects (errors).
- `warnings` — list of `ValidationFinding` objects (warnings).
- `error_count` and `warning_count`.
- `duration_ms` — the time taken by the layer.

### 8.3 Conflict Detection

The `ConflictDetector` analyses the blueprint for conflicts between features, technologies, components, or other elements. Each `ConflictFinding` has:
- `kind` — the conflict type.
- `severity` — `SEVERITY_ERROR` or `SEVERITY_WARNING`.
- `description` — human-readable description.
- `affected` — the affected elements.

### 8.4 Quality Scoring

The `QualityScorer` computes a `QualityScore` for the blueprint based on the error count and warning count. The `QualityScore` contains:
- `overall` — the overall quality score (0.0 to 1.0).
- `minimum_required` — the minimum required score to pass.
- `meets_minimum` — whether the overall score meets or exceeds the minimum.
- Per-dimension scores (completeness, consistency, buildability, etc.).

### 8.5 Approval Rules

The blueprint is **APPROVED** when **all three** conditions are met:

1. All six layers passed (no errors in any layer).
2. No error-severity conflicts were detected.
3. The quality score meets or exceeds the minimum required threshold.

Otherwise the report's `status` is `REJECTED` with a detailed list of all the reasons.

### 8.6 Constants

```python
ALL_LAYERS = ["layer1_basic_data", "layer2_features", "layer3_relationships",
              "layer4_execution_plan", "layer5_dependencies", "layer6_buildability"]
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
```

### 8.7 Data Model (BlueprintValidationReport)

The `BlueprintValidationReport` contains:
- `blueprint_name` — the name of the validated blueprint.
- `reviewed_at` — ISO timestamp of the review.
- `layers` — dict mapping layer name to `LayerResult`.
- `conflicts` — list of `ConflictFinding` objects.
- `missing_info` — list of `MissingInformationFinding` objects.
- `quality` — the `QualityScore`.
- `status` — `APPROVED` or `REJECTED`.
- `summary` — human-readable summary.
- `total_duration_ms` — total review duration.
- `is_approved` — convenience property checking status == APPROVED.
- `all_layers_passed` — whether all layers passed.
- `error_count` and `warning_count` — aggregated counts.

### 8.8 Output

The engine stores the `BlueprintValidationReport` in:
- `context.artefacts["blueprint_validation_report"]`
- `context.metadata["blueprint_validation_report"]`

If the report is rejected, the engine returns a `failed` result with all error messages from all layers and conflicts.

---

## 9. Engine 06 — Structure Generation Engine

### 9.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `structure_generator` |
| **Priority** | 60 |
| **Dependencies** | `["blueprint_validator"]` |
| **Version** | `1.0.0` |
| **Tags** | `["generation", "structure"]` |
| **Phase** | `create_structure` |
| **Source Files** | 7 files, 2,453 lines |
| **Output Artefact** | `project_structure_map` (type: `ProjectStructureMap`) |
| **Inputs** | `project_blueprint` + `blueprint_validation_report` |

The **Structure Generation Engine** is the first engine that starts building the project **physically**. It creates the professional project structure — the folder/file map — but it does **not** write code, functions, classes, or databases. Its sole function is to create the project structure map that later engines will fill.

### 9.2 Internal Steps

The engine executes 8 steps:

1. **Obtain the blueprint and validation report** from the context.
2. **Determine the root package name** using `NamingEngine.root_package_name()`.
3. **Build the complete folder map** using `FolderPlanner.plan()`.
4. **Build the component-to-folder mapping** — maps each component name to its folder path.
5. **Build the complete file map** using `FilePlanner.plan()`.
6. **Compute the build order** — folders first (sorted by build_order, then path), then files (sorted by build_order, then path).
7. **Validate the structure map** using `StructureValidator`.
8. **Store the structure map** in the context.

### 9.3 Sub-Modules

| File | Responsibility |
|------|----------------|
| `structure_generation_engine.py` | Main engine class with 8 steps |
| `structure_map.py` | Data classes: `FolderEntry`, `FileEntry`, `StructureRelationship`, `BuildOrderEntry`, `ProjectStructureMap` |
| `folder_planner.py` | `FolderPlanner` — builds the complete folder map |
| `file_planner.py` | `FilePlanner` — builds the complete file map |
| `naming_engine.py` | `NamingEngine` — naming conventions: root_package_name(), folder_name(), join_path() |
| `structure_validator.py` | `StructureValidator` — validates no duplicates, no conflicts, no empty folders, no files without responsibility |

### 9.4 Data Model (ProjectStructureMap)

The `ProjectStructureMap` contains:

- `project_name` — the project name.
- `root_path` — the root package path.
- `folders` — list of `FolderEntry` objects.
- `files` — list of `FileEntry` objects.
- `build_order` — list of `BuildOrderEntry` objects.
- `source_blueprint` — the name of the source blueprint.
- `validation_status` — the validation status from the blueprint validator.
- `component_to_folder` — mapping from component name to folder path.
- `summary` — human-readable summary.
- `notes` and `warnings` — supplementary information.

**FolderEntry** fields: path, kind, description, build_order, parent, subfolders, relationships, purpose.

**FileEntry** fields: path, kind, file_type, purpose, building_engine, build_order, relationships.

**BuildOrderEntry** fields: position, path, kind (folder/file), building_engine.

### 9.5 Output

The engine stores the `ProjectStructureMap` in:
- `context.artefacts["project_structure_map"]`
- `context.metadata["project_structure_map"]`

If the structure validation has errors, the engine returns a `failed` result.

---

## 10. Engine 07 — Component Detection Engine

### 10.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `component_detector` |
| **Priority** | 70 |
| **Dependencies** | `["structure_generator"]` |
| **Version** | `1.0.0` |
| **Tags** | `["generation", "detection", "components"]` |
| **Phase** | `detect_components` |
| **Source Files** | 11 files, 2,841 lines |
| **Output Artefact** | `component_registry` (type: `ComponentRegistry`) |
| **Inputs** | `project_blueprint` + `blueprint_validation_report` + `project_structure_map` |

The **Component Detection Engine** is responsible for detecting **all** software components the generated Telegram bot project will need **before** code generation begins. It does **not** write code, create files, build folders, or generate any project files. Its sole function is to detect, classify, validate, and order every software component.

### 10.2 Internal Steps

The engine executes 10 steps:

1. **Obtain the three artefacts** (blueprint, validation report, structure map) from the context.
2. **Scan and classify all components** using `TypeDetector.detect()` — detects component types (command, handler, service, repository, etc.).
3. **Resolve dependencies** using `RelationAnalyzer.analyze()` — builds edges between components and detects dangling dependencies.
4. **Detect and merge duplicates** using `DuplicateDetector.detect()` — finds components with the same name or responsibility and merges them.
5. **Re-resolve relations** after deduplication (reverse links may have changed).
6. **Validate the Single Responsibility Principle** using `ResponsibilityValidator.validate()` — ensures each component has exactly one clear responsibility.
7. **Check scalability** using `ScalabilityChecker.check()` — ensures the component design scales well.
8. **Check compatibility** using `CompatibilityChecker.check()` — ensures components are compatible with each other and with the blueprint.
9. **Validate quality rules** using `QualityRulesValidator.validate()` — checks for no unused components, no self-dependencies, no circular dependencies.
10. **Compute the build order** using `BuildOrderComputer.compute()` — topological sort of components.
11. **Assemble the Component Registry** — collects all findings, separates errors from warnings, builds the summary.
12. **Store the registry** in the context.

### 10.3 Sub-Modules

| File | Responsibility |
|------|----------------|
| `detection_engine.py` | Main engine class with 10 steps |
| `registry.py` | Data classes: `DetectedComponent`, `ComponentDependencyEdge`, `ComponentBuildOrderEntry`, `DetectionFinding`, `ComponentRegistry` |
| `type_detector.py` | `TypeDetector` — classifies components by type |
| `relation_analyzer.py` | `RelationAnalyzer` — resolves dependencies between components |
| `duplicate_detector.py` | `DuplicateDetector` — detects and merges duplicate components |
| `responsibility_validator.py` | `ResponsibilityValidator` — validates Single Responsibility Principle |
| `scalability_checker.py` | `ScalabilityChecker` — checks scalability |
| `compatibility_checker.py` | `CompatibilityChecker` — checks compatibility |
| `quality_validator.py` | `QualityRulesValidator` — validates quality rules (no unused, no self-dep, no cycles) |
| `build_order_computer.py` | `BuildOrderComputer` — computes build order via topological sort |

### 10.4 Data Model (ComponentRegistry)

The `ComponentRegistry` contains:

- `project_name` — the project name.
- `root_path` — the root package path.
- `components` — list of `DetectedComponent` objects.
- `relationships` — list of `ComponentDependencyEdge` objects.
- `build_order` — list of `ComponentBuildOrderEntry` objects.
- `source_blueprint` — the name of the source blueprint.
- `validation_status` — the validation status.
- `source_structure_map` — the name of the source structure map.
- `findings` — list of `DetectionFinding` objects.
- `summary` — human-readable summary.
- `notes` and `warnings` — supplementary information.
- `component_count` — convenience property.

**DetectedComponent** fields: name, display_name, type, kind, priority, description, source_feature, dependencies, file_path, folder_path, responsibility.

**ComponentDependencyEdge** fields: source, target, kind, description.

**ComponentBuildOrderEntry** fields: position, component_name, component_type, building_engine.

**DetectionFinding** fields: severity, code, message, affected.

### 10.5 Constants

```python
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
```

### 10.6 Output

The engine stores the `ComponentRegistry` in:
- `context.artefacts["component_registry"]`
- `context.metadata["component_registry"]`

If any error-level findings are detected, the engine returns a `failed` result.

---

## 11. Engine 08 — File Generation Planning Engine

### 11.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `file_planner` |
| **Priority** | 80 |
| **Dependencies** | `["component_detector"]` |
| **Version** | `1.0.0` |
| **Tags** | `["generation", "planning", "files"]` |
| **Phase** | `plan_files` |
| **Source Files** | 9 files, 2,638 lines |
| **Output Artefact** | `file_generation_plan` (type: `FileGenerationPlan`) |
| **Inputs** | `project_blueprint` + `blueprint_validation_report` + `project_structure_map` + `component_registry` |

The **File Generation Planning Engine** is the engine responsible for planning **all** files the generated Telegram bot project will contain **before** any file is created on disk. It does **not** write code, create files, build folders, or generate any project files. Its sole function is to analyse the project's components and structure map and produce a complete, validated `FileGenerationPlan` — the authoritative plan for every file the project will contain.

### 11.2 Internal Steps

The engine executes 9 steps:

1. **Obtain the four artefacts** (blueprint, validation report, structure map, component registry) from the context.
2. **Analyse all components and group their files** using `ComponentAnalyzer.analyze()` — groups files by component and identifies components without files.
3. **Determine the required files and their metadata** using `FileDeterminer.determine()` — determines which files each component needs and assigns metadata (file type, purpose, building engine).
4. **Resolve the relationships and dependencies between files** using `RelationshipResolver.resolve()` — builds edges between files and detects dangling dependencies.
5. **Compute the generation order** using `GenerationOrderComputer.compute()` — topological sort of files.
6. **Detect conflicts** using `ConflictDetector.detect()` — detects duplicates, naming conflicts, useless files, unlinked files, dangling and circular dependencies.
7. **Assemble the preliminary plan** — collects all findings.
8. **Validate the plan** using `PlanValidator.validate()` — validates that all components have files, all files have purpose, all relationships are valid, and the generation order is valid.
9. **Store the plan** in the context.

### 11.3 Sub-Modules

| File | Responsibility |
|------|----------------|
| `file_planning_engine.py` | Main engine class with 9 steps |
| `plan_data.py` | Data classes: `FilePlanEntry`, `FileRelationship`, `FileGenerationOrderEntry`, `PlanFinding`, `FileGenerationPlan` |
| `component_analyzer.py` | `ComponentAnalyzer` — analyses components and groups files |
| `file_determiner.py` | `FileDeterminer` — determines required files and metadata |
| `relationship_resolver.py` | `RelationshipResolver` — resolves file relationships and dependencies |
| `generation_order_computer.py` | `GenerationOrderComputer` — computes generation order (topological sort) |
| `conflict_detector.py` | `ConflictDetector` — detects file conflicts |
| `plan_validator.py` | `PlanValidator` — validates the file generation plan |

### 11.4 Data Model (FileGenerationPlan)

The `FileGenerationPlan` contains:

- `project_name` — the project name.
- `root_path` — the root package path.
- `files` — list of `FilePlanEntry` objects.
- `relationships` — list of `FileRelationship` objects.
- `generation_order` — list of `FileGenerationOrderEntry` objects.
- `source_blueprint` — the name of the source blueprint.
- `validation_status` — the validation status.
- `source_structure_map` — the name of the source structure map.
- `source_component_registry` — the name of the source component registry.
- `findings` — list of `PlanFinding` objects.
- `summary` — human-readable summary.
- `notes` and `warnings` — supplementary information.
- `file_count` — convenience property.

**FilePlanEntry** fields: path, file_type, purpose, building_engine, component, component_type, dependencies, build_order, metadata.

**FileRelationship** fields: source, target, kind, description.

**FileGenerationOrderEntry** fields: position, file_path, file_type, building_engine, component.

**PlanFinding** fields: severity, code, message, affected.

### 11.5 Output

The engine stores the `FileGenerationPlan` in:
- `context.artefacts["file_generation_plan"]`
- `context.metadata["file_generation_plan"]`

If any error-level findings are detected, the engine returns a `failed` result.

---

## 12. Engine 09 — Visual Page Reconstruction Engine

### 12.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `visual_page_reconstruction` |
| **Priority** | 90 |
| **Dependencies** | `["file_planner"]` |
| **Version** | `1.0.0` |
| **Tags** | `["pdf", "visual", "reconstruction"]` |
| **Phase** | (specialized — not part of the main build pipeline) |
| **Source Files** | 9 files, 3,284 lines |
| **Output Artefacts** | `page_analyses`, `rebuilt_pdf_bytes`, `visual_similarity_reports` |
| **Input** | `original_pdf` artefact (bytes, file path, or dict with 'bytes'/'path') |

The **Visual Page Reconstruction Engine** (also called PDFX AI) is a pixel-accurate PDF page reconstruction engine. It reads a PDF file, analyses every page element (images, text, choices, tables, equations, separators), and produces a rebuilt PDF that is visually indistinguishable from the original. This engine is specialized for PDF reconstruction and operates independently of the main bot-generation pipeline.

### 12.2 Design Principles

- **"The original is the reference."** No re-design, no visual improvement, no layout changes.
- **Pixel-accurate reconstruction.** Every element must be placed at its exact original position, size, rotation, and layer.
- **No element omission.** No element may be omitted, merged, or replaced.
- **Image fidelity.** Images must be extracted directly from the embedded stream with no compression, blur, or opacity changes.
- **Choice preservation.** All choices must maintain their original position, order, spacing, and shape.

### 12.3 The Four Phases

The engine operates in four phases:

**Phase 1 — Extraction:** Open the PDF using `pdfplumber`, iterate over all pages, and analyse each page using `PageAnalyzer.analyse()`. Extract all images from the embedded PDF stream using `ImageExtractor`.

**Phase 2 — Analysis:** For each page, the `PageAnalyzer` detects all elements:
- Images (`PageImage`)
- Text content (`PageText`)
- Choices (`PageChoice`)
- Tables (`PageTable`)
- Equations (`PageEquation`)
- Separators (`PageSeparator`)
- Shapes

**Phase 3 — Reconstruction:** The `LayoutRebuilder.rebuild_all_pages()` rebuilds all pages with pixel-accurate fidelity, using the `CoordinateMapper` to map coordinates and the `ChoiceDetector` to detect and preserve choices.

**Phase 4 — Validation:** The `VisualValidator.validate()` validates each page against the original analysis, producing a `VisualSimilarityReport` with an overall score. The minimum accuracy threshold is **95%** (`VISUAL_ACCURACY_THRESHOLD = 0.95`).

### 12.4 Element Types

```python
ELEMENT_TYPE_IMAGE = "image"
ELEMENT_TYPE_TEXT = "text"
ELEMENT_TYPE_CHOICE = "choice"
ELEMENT_TYPE_TABLE = "table"
ELEMENT_TYPE_EQUATION = "equation"
ELEMENT_TYPE_SEPARATOR = "separator"
ELEMENT_TYPE_SHAPE = "shape"
```

### 12.5 Visual Layers

```python
VISUAL_LAYER_BACKGROUND = "background"  # Page background (colour, pattern)
VISUAL_LAYER_IMAGE = "image"            # Images extracted from the PDF
VISUAL_LAYER_SHAPE = "shape"            # Vector shapes (lines, rectangles)
VISUAL_LAYER_TEXT = "text"              # All text content
VISUAL_LAYER_OVERLAY = "overlay"        # Overlays, watermarks, annotations
```

### 12.6 Sub-Modules

| File | Responsibility |
|------|----------------|
| `page_reconstruction_engine.py` | Main engine class with 4 phases |
| `page_analysis.py` | Data classes: `PageAnalysis`, `PageDimensions`, `PageImage`, `PageText`, `PageChoice`, `PageTable`, `PageEquation`, `PageSeparator`, `ElementPosition`, `VisualLayer` |
| `page_analyzer.py` | `PageAnalyzer` — analyses a single page |
| `image_extractor.py` | `ImageExtractor` — extracts images from the PDF embedded stream |
| `layout_rebuilder.py` | `LayoutRebuilder` — rebuilds pages with pixel-accurate fidelity |
| `choice_detector.py` | `ChoiceDetector` — detects and preserves choices |
| `coordinate_mapper.py` | `CoordinateMapper` — maps coordinates between original and rebuilt pages |
| `visual_validator.py` | `VisualValidator` — validates visual similarity (95% threshold) |

### 12.7 External Dependency

The engine uses the `pdfplumber` library for PDF parsing. It is imported conditionally:

```python
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
```

### 12.8 Output

The engine produces:
- `page_analyses` — list of `PageAnalysis` objects (one per page).
- `rebuilt_pdf_bytes` — raw PDF bytes of the rebuilt document.
- `visual_similarity_reports` — list of `VisualSimilarityReport` objects (one per page).
- `total_pages`, `total_elements`, `total_images`, `overall_passed`, `duration_ms`.

### 12.9 Convenience Methods

The engine also provides:
- `analyse_page(pdf_bytes, page_number)` — analyse a single page without the full pipeline.
- `validate_reconstruction(original_analysis, rebuilt_positions)` — validate a single page reconstruction.

---

## 13. Engine 09b — Dependency Resolution Engine

### 13.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `dependency_resolver` |
| **Priority** | 95 |
| **Dependencies** | `["file_planner"]` |
| **Version** | `1.0.0` |
| **Tags** | `["generation", "dependencies", "resolution"]` |
| **Phase** | `resolve_dependencies` |
| **Source Files** | 11 files, 4,248 lines (the largest engine) |
| **Output Artefact** | `dependency_resolution_report` (type: `DependencyResolutionReport`) |
| **Inputs** | `project_blueprint` + `blueprint_validation_report` + `project_structure_map` + `component_registry` + `file_generation_plan` |

The **Dependency Resolution Engine** is the engine responsible for building the complete, authoritative dependency map for the generated Telegram bot project **before** any code is written or any file is created on disk. It does **not** write code, create files, install libraries, or add dependencies. Its sole function is to analyse the project's components and structure and produce a complete, validated `DependencyResolutionReport` — the authoritative dependency map for every library, framework, and tool the project will use.

### 13.2 Internal Steps

The engine executes 11 steps:

1. **Obtain the five artefacts** (blueprint, validation report, structure map, component registry, file plan) from the context.
2. **Analyse all components** using `ComponentAnalyzer.analyze()` — determines required libraries per component.
3. **Determine the required dependencies** using `LibraryDeterminer.determine()` — determines which libraries, frameworks, and tools are needed, with versions, reasons, sources, and priorities.
4. **Build the dependency graph** using `DependencyGraphBuilder.build()` — builds relationships and load order.
5. **Check compatibility** using `CompatibilityChecker.check()` — checks language, framework, OS, and inter-library compatibility.
6. **Detect conflicts** using `ConflictDetector.detect()` — detects version conflicts, duplicates, unused dependencies, circular dependencies, and broken dependencies.
7. **Optimise the dependency list** using `DependencyOptimizer.optimize()` — minimises, prefers official, avoids abandoned/unstable libraries.
8. **Flag security risks** using `SecurityChecker.check()` — flags bad reputation, untrusted, and known-vulnerable versions.
9. **Assemble the preliminary report** — collects all findings.
10. **Validate the report** using `PlanValidator.validate()` — validates all deps complete, no conflicts, valid relationships, buildable.
11. **Store the report** in the context.

### 13.3 Sub-Modules

| File | Responsibility |
|------|----------------|
| `dependency_resolution_engine.py` | Main engine class with 11 steps |
| `report_data.py` | Data classes: `DependencyEntry`, `DependencyRelationship`, `DependencyOrderEntry`, `ResolutionFinding`, `DependencyResolutionReport` |
| `component_analyzer.py` | `ComponentAnalyzer` — analyses components and determines required libraries |
| `library_determiner.py` | `LibraryDeterminer` — determines required dependencies with metadata |
| `dependency_graph_builder.py` | `DependencyGraphBuilder` — builds dependency graph, relationships, load order |
| `compatibility_checker.py` | `CompatibilityChecker` — checks compatibility (language, framework, OS, inter-library) |
| `conflict_detector.py` | `ConflictDetector` — detects version conflicts, duplicates, unused, circular, broken deps |
| `optimizer.py` | `DependencyOptimizer` — optimises the dependency list |
| `security_checker.py` | `SecurityChecker` — flags security risks |
| `plan_validator.py` | `PlanValidator` — validates the resolution report |

### 13.4 Data Model (DependencyResolutionReport)

The `DependencyResolutionReport` contains:

- `project_name` — the project name.
- `language` — the programming language (Python).
- `language_version` — the language version (3.11).
- `framework` — the framework (python-telegram-bot).
- `dependencies` — list of `DependencyEntry` objects.
- `relationships` — list of `DependencyRelationship` objects.
- `load_order` — list of `DependencyOrderEntry` objects.
- `source_blueprint` — the name of the source blueprint.
- `validation_status` — the validation status.
- `source_structure_map`, `source_component_registry`, `source_file_generation_plan` — source artefact names.
- `findings` — list of `ResolutionFinding` objects.
- `summary` — human-readable summary.
- `notes` and `warnings` — supplementary information.
- `dependency_count` — convenience property.

**DependencyEntry** fields: name, version, kind, category, reason, source_component, priority, required, optional, alternatives, metadata.

**DependencyRelationship** fields: source, target, kind, description.

**DependencyOrderEntry** fields: position, dependency_name, kind, category.

**ResolutionFinding** fields: severity, code, message, affected, category.

### 13.5 Output

The engine stores the `DependencyResolutionReport` in:
- `context.artefacts["dependency_resolution_report"]`
- `context.metadata["dependency_resolution_report"]`

If any error-level findings are detected, the engine returns a `failed` result.

---

## 14. Engine 10 — Project Context Engine

### 14.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `project_context` |
| **Priority** | 96 |
| **Dependencies** | `["dependency_resolver"]` |
| **Version** | `1.0.0` |
| **Tags** | `["generation", "context", "merging"]` |
| **Phase** | `build_context` |
| **Source Files** | 12 files, 3,663 lines |
| **Output Artefact** | `project_context` (type: `ProjectContext`) |
| **Inputs** | 6 artefacts: `project_blueprint` + `blueprint_validation_report` + `project_structure_map` + `component_registry` + `file_generation_plan` + `dependency_resolution_report` |

The **Project Context Engine** is the engine responsible for building the complete, authoritative, unified understanding of the entire project **before** any code is written or any file is created on disk. It does **not** write code, create files, or make build decisions. Its sole function is to merge the six upstream artefacts into a single, validated `ProjectContext` — the single authoritative context that every downstream engine can query for any piece of project information.

### 14.2 The Six Readers

The engine uses six reader classes, one per upstream artefact:

| Reader | File | Artefact | Output |
|--------|------|----------|--------|
| `BlueprintReader` | `blueprint_reader.py` | `project_blueprint` | goal, features, relationships, stages, expansion_points |
| `ValidationReader` | `validation_reader.py` | `blueprint_validation_report` | validation_status, quality_scores, overall_quality, findings, provenance_partial |
| `StructureReader` | `structure_reader.py` | `project_structure_map` | files, relationships, expansion_points, build_order_map, provenance_partial |
| `RegistryReader` | `registry_reader.py` | `component_registry` | components, relationships, expansion_points, build_order_map, provenance_partial |
| `FilePlanReader` | `file_plan_reader.py` | `file_generation_plan` | files, relationships, expansion_points, build_order_map, provenance_partial |
| `DependencyReader` | `dependency_reader.py` | `dependency_resolution_report` | dependencies, relationships, findings, load_order_map, provenance_partial |

Each reader returns a dictionary with the extracted data and a `provenance_partial` — a mapping from element names to their source artefact.

### 14.3 The Context Assembler

The `ContextAssembler` merges the output of all six readers into a unified model:

- **Merges files** — the file plan is authoritative; the structure map fills gaps for files not in the file plan.
- **Deduplicates relationships** — relationships are deduplicated by (source, target, kind).
- **Enriches stages** — stages from the blueprint's `ExecutionPlan.phases` are enriched with components and dependencies.
- **Cross-links** — features ↔ components, components ↔ files, components ↔ dependencies are cross-linked.
- **Builds provenance** — a `SourceProvenance` mapping that records which artefact each piece of information came from.

### 14.4 The Context Linker

The `ContextLinker` builds the context graph with **12 O(1) look-up indices**:

1. `feature_to_components` — Feature → Components
2. `component_to_features` — Component → Features
3. `component_to_files` — Component → Files
4. `file_to_components` — File → Components
5. `component_to_dependencies` — Component → Dependencies
6. `dependency_to_components` — Dependency → Components
7. `component_to_stage` — Component → Execution Stage
8. `stage_to_components` — Execution Stage → Components
9. `feature_to_stage` — Feature → Execution Stage
10. `stage_to_features` — Execution Stage → Features
11. `dependency_to_stage` — Dependency → Execution Stage
12. `stage_to_dependencies` — Execution Stage → Dependencies

The linker also builds the list of `ContextLink` objects — each representing an edge in the context graph with a `kind` (one of `LINK_FEATURE_TO_COMPONENT`, `LINK_COMPONENT_TO_FILE`, `LINK_FILE_TO_DEPENDENCY`, `LINK_DEPENDENCY_TO_STAGE`, `LINK_COMPONENT_TO_STAGE`, `LINK_FEATURE_TO_STAGE`).

### 14.5 The Context Validator

The `ContextValidator` validates the merged context for internal consistency. It checks for:

- **Duplicate features** — no two features with the same name.
- **Duplicate components** — no two components with the same name.
- **Duplicate files** — no two files with the same path.
- **Duplicate dependencies** — no two dependencies with the same name.
- **Features without components** — every feature must have at least one component.
- **Components without files** — every component must have at least one file.
- **Files without responsibility** — every file must have a purpose/responsibility.
- **Unknown elements in relationships** — no relationship may reference an unknown element.
- **Stages without components** — every stage must have at least one component.
- **Orphaned components** — no component may exist without being linked to a feature or stage.

Each finding is a `ContextFinding` with a severity (`SEVERITY_ERROR`, `SEVERITY_WARNING`, `SEVERITY_INFO`), a code, a message, and an affected element.

### 14.6 Data Model (ProjectContext)

The `ProjectContext` contains:

- `goal: ProjectGoal` — the project's high-level goal (name, description, bot_type, language, framework, database).
- `features: List[FeatureSummary]` — the project's features.
- `components: List[ComponentSummary]` — the project's components.
- `files: List[FileSummary]` — the project's files.
- `dependencies: List[DependencySummary]` — the project's dependencies.
- `relationships: List[RelationshipSummary]` — the relationships between elements.
- `stages: List[ExecutionStage]` — the execution stages.
- `links: List[ContextLink]` — the context graph edges.
- `link_indices: LinkIndices` — the 12 O(1) look-up indices.
- `expansion_points: List[ExpansionPoint]` — areas for future expansion.
- `findings: List[ContextFinding]` — validation findings.
- `provenance: SourceProvenance` — traceability mapping.
- `summary: str` — human-readable summary.
- `notes: List[str]` and `warnings: List[str]` — supplementary information.
- `created_at: str` — ISO timestamp.

**Convenience properties:** `feature_count`, `component_count`, `file_count`, `dependency_count`, `relationship_count`, `stage_count`, `link_count`, `expansion_point_count`, `has_findings`, `error_count`, `warning_count`, `info_count`.

**O(1) look-up methods:** `get_components_for_feature(name)`, `get_files_for_component(name)`, `get_dependencies_for_component(name)`, `get_stage_for_component(name)`, `get_components_for_stage(name)`, `get_features_for_stage(name)`, `get_dependencies_for_stage(name)`, `get_stage_for_feature(name)`, `get_stage_for_dependency(name)`.

### 14.7 Source Artefact Constants

```python
SOURCE_BLUEPRINT = "blueprint"
SOURCE_VALIDATION = "validation"
SOURCE_STRUCTURE = "structure"
SOURCE_COMPONENT_REGISTRY = "component_registry"
SOURCE_FILE_PLAN = "file_plan"
SOURCE_DEPENDENCY_REPORT = "dependency_report"
ALL_SOURCES = [SOURCE_BLUEPRINT, SOURCE_VALIDATION, SOURCE_STRUCTURE,
                SOURCE_COMPONENT_REGISTRY, SOURCE_FILE_PLAN, SOURCE_DEPENDENCY_REPORT]
```

### 14.8 Link Kind Constants

```python
LINK_FEATURE_TO_COMPONENT = "feature_to_component"
LINK_COMPONENT_TO_FILE = "component_to_file"
LINK_FILE_TO_DEPENDENCY = "file_to_dependency"
LINK_DEPENDENCY_TO_STAGE = "dependency_to_stage"
LINK_COMPONENT_TO_STAGE = "component_to_stage"
LINK_FEATURE_TO_STAGE = "feature_to_stage"
ALL_LINK_KINDS = [LINK_FEATURE_TO_COMPONENT, LINK_COMPONENT_TO_FILE,
                   LINK_FILE_TO_DEPENDENCY, LINK_DEPENDENCY_TO_STAGE,
                   LINK_COMPONENT_TO_STAGE, LINK_FEATURE_TO_STAGE]
```

### 14.9 Sub-Modules

| File | Lines | Responsibility |
|------|-------|----------------|
| `project_context_engine.py` | ~414 | Main engine class |
| `context_data.py` | ~1,057 | All data classes and constants |
| `blueprint_reader.py` | ~217 | Reads the project blueprint |
| `validation_reader.py` | ~159 | Reads the validation report |
| `structure_reader.py` | ~152 | Reads the structure map |
| `registry_reader.py` | ~141 | Reads the component registry |
| `file_plan_reader.py` | ~142 | Reads the file generation plan |
| `dependency_reader.py` | ~145 | Reads the dependency resolution report |
| `context_assembler.py` | ~443 | Merges all readers' output |
| `context_linker.py` | ~302 | Builds 12 O(1) link indices |
| `context_validator.py` | ~360 | Validates context integrity |
| `__init__.py` | ~131 | Package exports |

### 14.10 Output

The engine stores the `ProjectContext` in:
- `context.artefacts["project_context"]`
- `context.metadata["project_context"]`

---

## 15. Engine 11 — Project Intelligence Graph Engine

### 15.1 Overview

| Property | Value |
|----------|-------|
| **Engine ID** | `intelligence_graph` |
| **Priority** | 97 |
| **Dependencies** | `["project_context"]` |
| **Version** | `1.0.0` |
| **Tags** | `["generation", "graph", "navigation"]` |
| **Phase** | `build_graph` |
| **Source Files** | 7 files, 4,002 lines |
| **Output Artefact** | `intelligence_graph` (type: `ProjectIntelligenceGraph`) |
| **Inputs** | 7 artefacts: `project_blueprint` + `blueprint_validation_report` + `project_structure_map` + `component_registry` + `file_generation_plan` + `dependency_resolution_report` + `project_context` |

The **Project Intelligence Graph Engine** is the engine responsible for building the complete, authoritative, intelligent graph of the entire project **before** any code is written or any file is created on disk. It does **not** write code, create files, or make build decisions. Its sole function is to convert all seven upstream artefacts into a single `ProjectIntelligenceGraph` — a typed graph with **19 node types** and **12 edge kinds**, precomputed **O(1) look-up indices**, circular-dependency detection, structural-problem detection, and internal-consistency validation. The graph is the **single reference point** for all downstream engines: instead of re-reading the seven upstream artefacts, every downstream engine reads the graph and uses the precomputed indices to access any piece of information in O(1) time and reach any element in very few steps.

### 15.2 The Four Sub-Components

The engine delegates its work to four specialised sub-components, each with a single responsibility:

| Sub-Component | File | Responsibility |
|---------------|------|----------------|
| `GraphBuilder` | `graph_builder.py` | Converts all 7 artefacts into graph nodes and edges |
| `GraphNavigator` | `graph_navigator.py` | Builds the O(1) look-up indices for fast traversal |
| `CircularDetector` | `circular_detector.py` | Detects circular dependencies and structural problems |
| `GraphValidator` | `graph_validator.py` | Validates the graph for internal consistency |

### 15.3 The Graph Builder

The `GraphBuilder` is the heart of the engine. It reads all seven upstream artefacts and converts every element into a `GraphNode`, and every relationship into a `GraphEdge`. The builder creates the following node types from each artefact:

- **From the Project Blueprint (`project_blueprint`):** project node, feature nodes, stage nodes, route nodes, command nodes, environment variable nodes.
- **From the Component Registry (`component_registry`):** component nodes, service nodes, middleware nodes, repository nodes.
- **From the Project Structure Map (`project_structure_map`):** folder nodes, file nodes.
- **From the File Generation Plan (`file_generation_plan`):** file nodes (enriched with building-engine and source-component metadata).
- **From the Dependency Resolution Report (`dependency_resolution_report`):** dependency nodes, library nodes, database table nodes.
- **From the Project Context (`project_context`):** configuration nodes, additional cross-links.

The builder then creates the following edge kinds:

- **`EDGE_CONTAINS`** — a project contains features, components, folders, files, stages, routes, commands, configurations, environment variables; a folder contains files; a stage contains components.
- **`EDGE_DEPENDS_ON`** — a component depends on a dependency, library, or database table.
- **`EDGE_REQUIRED_BY`** — the reverse of `EDGE_DEPENDS_ON` (a dependency is required by a component). This is intentionally excluded from circular-dependency detection to avoid false 2-cycles.
- **`EDGE_USES`** — a file uses a dependency or a file uses another file.
- **`EDGE_REFERENCES`** — a component references a file, a feature references a component, a file references a dependency.
- **`EDGE_CREATES`** — a component creates a file.
- **`EDGE_IMPLEMENTS`** — a component implements an interface or feature.
- **`EDGE_CALLS`** — a component or file calls a function.
- **`EDGE_READS`** — a component reads a configuration or environment variable.
- **`EDGE_WRITES`** — a component writes to a database table or configuration.
- **`EDGE_EXTENDS`** — a class extends another class.
- **`EDGE_IMPORTS`** — a file imports a dependency.

The builder uses the format `"<type>:<name>"` for node IDs (e.g. `"component:database"`, `"dependency:SQLAlchemy"`) and `"<source_id>--<kind>-->[target_id]"` for edge IDs, ensuring globally unique identifiers.

### 15.4 The Graph Navigator

The `GraphNavigator` builds the **11 O(1) look-up indices** stored in `GraphIndices`:

1. `node_by_id` — Node ID → `GraphNode`.
2. `nodes_by_type` — Node type → list of node IDs.
3. `node_by_name` — Element name → node ID (for type-unambiguous names; the first registered wins).
4. `node_id_by_type_and_name` — (type, name) → node ID (for disambiguated look-ups).
5. `edges_by_source` — Source node ID → list of `GraphEdge` objects.
6. `edges_by_target` — Target node ID → list of `GraphEdge` objects.
7. `out_edges` — Source node ID → list of target node IDs.
8. `in_edges` — Target node ID → list of source node IDs.
9. `out_edges_by_kind` — (source node ID, edge kind) → list of target node IDs.
10. `in_edges_by_kind` — (target node ID, edge kind) → list of source node IDs.
11. `edges_by_kind` — Edge kind → list of `GraphEdge` objects.

The `ProjectIntelligenceGraph` exposes all of these indices through convenience methods: `get_node(node_id)`, `get_node_by_name(name)`, `get_node_by_type_and_name(type, name)`, `nodes_of_type(type)`, `node_ids_of_type(type)`, `outgoing(node_id)`, `incoming(node_id)`, `outgoing_by_kind(node_id, kind)`, `incoming_by_kind(node_id, kind)`, `edges_from(node_id)`, `edges_to(node_id)`, `edges_of_kind(kind)`, `neighbours(node_id)`.

For multi-hop navigation, the graph provides `reachable(node_id, max_hops=8)` (breadth-first traversal) and `shortest_path(source_id, target_id, max_hops=16)` (breadth-first search).

### 15.5 The Circular Detector

The `CircularDetector` finds structural problems in the graph. It uses a **three-colour DFS** (WHITE/GREY/BLACK) with a recursion stack to detect circular dependencies in O(V+E) time. The detector performs five checks:

1. **Circular dependencies** (`CATEGORY_CIRCULAR_DEPENDENCY`) — finds cycles in the dependency sub-graph. Only forward edges (`EDGE_DEPENDS_ON`, `EDGE_IMPORTS`, `EDGE_USES`) are followed; `EDGE_REQUIRED_BY` is intentionally excluded because it is the reverse of `EDGE_DEPENDS_ON` and would produce a false 2-cycle for every component-dependency pair. Cycles are normalised by rotating so the lexicographically smallest node ID is first, to avoid reporting the same cycle multiple times.
2. **Broken references** (`CATEGORY_BROKEN_REFERENCE`) — finds edges whose source or target node does not exist.
3. **Unused components** (`CATEGORY_UNUSED_COMPONENT`) — finds components that are not required by any other component.
4. **Orphan files** (`CATEGORY_ORPHAN_FILE`) — finds files that are not contained in any folder.
5. **Dead components** (`CATEGORY_DEAD_COMPONENT`) — finds components that have no outgoing edges (they do not depend on anything and nothing depends on them).

Each finding is a `GraphFinding` with a severity (`SEVERITY_ERROR`, `SEVERITY_WARNING`, `SEVERITY_INFO`), a code, a message, an affected element, a category, an optional resolution hint, and (for circular-dependency findings) the list of node IDs that form the cycle.

### 15.6 The Graph Validator

The `GraphValidator` validates the graph for internal consistency. It performs nine checks:

1. **Duplicate node IDs** — no two nodes may have the same ID.
2. **Duplicate edge IDs** — no two edges may have the same ID.
3. **Edges reference existing nodes** — every edge's source and target must exist in the graph.
4. **Node types are valid** — every node's type must be one of the `NODE_TYPE_*` constants.
5. **Edge kinds are valid** — every edge's kind must be one of the `EDGE_*` constants.
6. **Node required fields** — every node must have a non-empty ID, type, and name.
7. **No self-loops** — no edge may have the same source and target.
8. **Project node exists** — the graph must contain exactly one project node.
9. **Indices consistency** — the precomputed indices must be consistent with the nodes and edges.

### 15.7 Data Model (ProjectIntelligenceGraph)

The `ProjectIntelligenceGraph` contains:

- `nodes: List[GraphNode]` — the graph nodes (19 types).
- `edges: List[GraphEdge]` — the graph edges (12 kinds).
- `indices: GraphIndices` — the 11 O(1) look-up indices.
- `findings: List[GraphFinding]` — validation findings from the detector and validator.
- `provenance: GraphProvenance` — traceability record (which artefacts were used).
- `summary: str` — human-readable summary.
- `notes: List[str]` and `warnings: List[str]` — supplementary information.

**GraphNode** fields: `node_id` (format `"<type>:<name>"`), `type` (one of 19 `NODE_TYPE_*` constants), `name`, `display_name`, `description`, `priority` (lower values built first), `owner_engine`, `source` (which `SOURCE_*` artefact), `metadata` (type-specific), `neighbours` (convenience list of connected node IDs).

**GraphEdge** fields: `edge_id` (format `"<source_id>--<kind>-->[target_id]"`), `source_id`, `target_id`, `kind` (one of 12 `EDGE_*` constants), `source` (which `SOURCE_*` artefact), `description`.

**GraphFinding** fields: `severity` (`SEVERITY_ERROR`/`SEVERITY_WARNING`/`SEVERITY_INFO`), `code`, `message`, `affected`, `category` (one of `CATEGORY_*` constants), `resolution_hint`, `cycle` (for circular-dependency findings).

**GraphProvenance** fields: `project_name`, `blueprint_name`, `validation_status`, `structure_map_name`, `component_registry_name`, `file_plan_name`, `dependency_report_name`, `project_context_name`, `all_sources_used`.

**Convenience properties on `ProjectIntelligenceGraph`:** `node_count`, `edge_count`, `finding_count`, `is_empty`, `has_errors`, `error_count`, `warning_count`, `node_type_count`, `edge_kind_count`.

**O(1) look-up methods:** `get_node(node_id)`, `get_node_by_name(name)`, `get_node_by_type_and_name(type, name)`, `nodes_of_type(type)`, `node_ids_of_type(type)`, `outgoing(node_id)`, `incoming(node_id)`, `outgoing_by_kind(node_id, kind)`, `incoming_by_kind(node_id, kind)`, `edges_from(node_id)`, `edges_to(node_id)`, `edges_of_kind(kind)`, `neighbours(node_id)`.

**Multi-hop navigation methods:** `reachable(node_id, max_hops=8)`, `shortest_path(source_id, target_id, max_hops=16)`.

### 15.8 Node-Type Constants (19)

```python
NODE_TYPE_PROJECT = "project"
NODE_TYPE_FOLDER = "folder"
NODE_TYPE_FILE = "file"
NODE_TYPE_CLASS = "class"
NODE_TYPE_FUNCTION = "function"
NODE_TYPE_INTERFACE = "interface"
NODE_TYPE_COMPONENT = "component"
NODE_TYPE_FEATURE = "feature"
NODE_TYPE_DEPENDENCY = "dependency"
NODE_TYPE_LIBRARY = "library"
NODE_TYPE_DATABASE_TABLE = "database_table"
NODE_TYPE_ROUTE = "route"
NODE_TYPE_COMMAND = "command"
NODE_TYPE_CONFIGURATION = "configuration"
NODE_TYPE_ENVIRONMENT_VARIABLE = "environment_variable"
NODE_TYPE_SERVICE = "service"
NODE_TYPE_MIDDLEWARE = "middleware"
NODE_TYPE_REPOSITORY = "repository"
NODE_TYPE_STAGE = "stage"
```

### 15.9 Edge-Kind Constants (12)

```python
EDGE_USES = "uses"
EDGE_IMPORTS = "imports"
EDGE_DEPENDS_ON = "depends_on"
EDGE_CALLS = "calls"
EDGE_CREATES = "creates"
EDGE_READS = "reads"
EDGE_WRITES = "writes"
EDGE_EXTENDS = "extends"
EDGE_IMPLEMENTS = "implements"
EDGE_CONTAINS = "contains"
EDGE_REFERENCES = "references"
EDGE_REQUIRED_BY = "required_by"
```

### 15.10 Source-Artefact Constants (7)

```python
SOURCE_BLUEPRINT = "blueprint"
SOURCE_VALIDATION = "validation"
SOURCE_STRUCTURE = "structure"
SOURCE_COMPONENT_REGISTRY = "component_registry"
SOURCE_FILE_PLAN = "file_plan"
SOURCE_DEPENDENCY_REPORT = "dependency_report"
SOURCE_PROJECT_CONTEXT = "project_context"
```

### 15.11 Finding-Category Constants (7)

```python
CATEGORY_CIRCULAR_DEPENDENCY = "circular_dependency"
CATEGORY_BROKEN_REFERENCE = "broken_reference"
CATEGORY_UNUSED_COMPONENT = "unused_component"
CATEGORY_ORPHAN_FILE = "orphan_file"
CATEGORY_DEAD_COMPONENT = "dead_component"
CATEGORY_CONSISTENCY = "consistency"
CATEGORY_STRUCTURE = "structure"
```

### 15.12 Sub-Modules

| File | Lines | Responsibility |
|------|-------|----------------|
| `intelligence_graph_engine.py` | ~470 | Main engine class — orchestrates builder, navigator, detector, validator |
| `graph_data.py` | ~849 | All data classes and constants (19 node types, 12 edge kinds, 7 sources, 7 categories) |
| `graph_builder.py` | ~1,483 | Converts all 7 artefacts into graph nodes and edges |
| `graph_navigator.py` | ~159 | Builds the 11 O(1) look-up indices |
| `circular_detector.py` | ~429 | Detects circular dependencies (3-colour DFS), broken references, unused components, orphan files, dead components |
| `graph_validator.py` | ~438 | Validates graph for internal consistency (9 checks) |
| `__init__.py` | ~174 | Package exports |

### 15.13 Output

The engine stores the `ProjectIntelligenceGraph` in:
- `context.artefacts["intelligence_graph"]`
- `context.metadata["intelligence_graph"]`

---

## 16. Pipeline Architecture & Data Flow

### 16.1 Engine Execution Order

The Core Engine Manager uses topological sorting based on priorities and dependencies to determine the execution order. The registered order is:

| Order | Engine ID | Priority | Dependencies | Output Artefact |
|-------|-----------|----------|--------------|-----------------|
| 1 | `analyzer` | 10 | `[]` | `analysis_report` |
| 2 | `intent_parser` | 20 | `["analyzer"]` | `intent` |
| 3 | `blueprint_composer` | 30 | `["analyzer", "intent_parser"]` | `blueprint` |
| 4 | `project_planner` | 40 | `["analyzer"]` | `project_blueprint` |
| 5 | `blueprint_validator` | 50 | `["project_planner"]` | `blueprint_validation_report` |
| 6 | `structure_generator` | 60 | `["blueprint_validator"]` | `project_structure_map` |
| 7 | `component_detector` | 70 | `["structure_generator"]` | `component_registry` |
| 8 | `file_planner` | 80 | `["component_detector"]` | `file_generation_plan` |
| 9 | `visual_page_reconstruction` | 90 | `["file_planner"]` | `page_analyses`, `rebuilt_pdf_bytes`, `visual_similarity_reports` |
| 10 | `dependency_resolver` | 95 | `["file_planner"]` | `dependency_resolution_report` |
| 11 | `project_context` | 96 | `["dependency_resolver"]` | `project_context` |
| 12 | `intelligence_graph` | 97 | `["project_context"]` | `intelligence_graph` |

### 16.2 Artefact Flow Diagram

```
User Request (raw text)
     │
     ▼
[Engine 01: Analyzer] ──→ analysis_report
     │
     ▼
[Engine 02: Intent Parser] ──→ intent
     │
     ▼
[Engine 03: Blueprint Composer] ──→ blueprint (legacy)
     │
     ▼
[Engine 04: Project Planner] ──→ project_blueprint
     │                          │
     ▼                          │
[Engine 05: Blueprint Validator] ──→ blueprint_validation_report
     │                          │           │
     ▼                          │           │
[Engine 06: Structure Generator] ──→ project_structure_map
     │                          │           │           │
     ▼                          │           │           │
[Engine 07: Component Detector] ──→ component_registry
     │                          │           │           │           │
     ▼                          │           │           │           │
[Engine 08: File Planner] ──→ file_generation_plan
     │                      │           │           │           │
     ├──→ [Engine 09: Visual Reconstructor] ──→ page_analyses, rebuilt_pdf
     │                      │           │           │           │
     ▼                      │           │           │           │
[Engine 09b: Dependency Resolver] ──→ dependency_resolution_report
     │              │           │           │           │           │
     ▼              │           │           │           │           │
[Engine 10: Project Context] ──→ project_context
                                (merges ALL 6 artefacts:
                                 project_blueprint +
                                 blueprint_validation_report +
                                 project_structure_map +
                                 component_registry +
                                 file_generation_plan +
                                 dependency_resolution_report)
     |
     v
[Engine 11: Intelligence Graph] --> intelligence_graph
                                   (converts ALL 7 artefacts into a
                                    single Project Intelligence Graph
                                    with 19 node types, 12 edge kinds,
                                    11 O(1) indices, and circular-
                                    dependency detection)
```

### 16.3 The GenerationContext as the Communication Bus

All artefacts flow through the `GenerationContext.artefacts` dictionary. No engine ever accesses another engine directly. The context is the sole communication channel:

```
Engine A writes: context.set("artefact_name", value)
Engine B reads:  value = context.get("artefact_name")
```

Every engine also stores its output in `context.metadata` for easy access by the pipeline and external tools.

### 16.4 The Pipeline Orchestrator

The `PipelineOrchestrator` drives the full generation lifecycle. It builds the ordered list of pipeline stages:

1. `ParseStage` — parses the request.
2. `ComposeBlueprintStage` — composes the blueprint.
3. `ValidateBlueprintStage` — validates the blueprint.
4. `GenerateStage` — generates the project.
5. `ValidateOutputStage` — validates the output.
6. `PackageStage` — packages the final project.

The orchestrator is **fail-fast**: it stops the pipeline on the first failing stage when `fail_fast` is enabled in the configuration (default: `True`).

---

## 17. Core Engine Manager

### 17.1 Overview

The **Core Engine Manager** (`CoreEngineManager`) is the sole authority over every engine in the system. It does **not** generate code, create files, or analyse requests. Its responsibilities are:

1. **Registration** — register every engine with a unique ID, name, version, status, priority, dependencies, and enabled flag. No duplicate IDs are allowed.

2. **Lifecycle enforcement** — drive every engine through the states: `Registered → Loaded → Initialized → Ready → Running → Completed` (or `Failed`). No stage may be skipped.

3. **Dependency validation** — before running any engine, verify that all its declared dependencies have completed successfully. If any dependency is missing or unmet, the engine does not run and the pipeline is stopped.

4. **Execution queue** — maintain an internal queue that determines the order in which engines run. No engine can change its own order.

5. **Error management** — if any engine fails, stop the entire pipeline. Log the failure reason, the engine name, and the stage where the error occurred. No continuation is allowed.

6. **Logging** — log every operation: loading, starting, completing, failing, stopping, and the execution duration of each engine.

7. **Security** — enforce four rules:
   - Unregistered engines cannot run.
   - Engines not in the `Ready` state cannot run.
   - Engines cannot start themselves directly.
   - Engines cannot bypass the manager.

8. **Clear interfaces** — no engine accesses another engine directly. All communication flows through the manager (and the GenerationContext).

9. **Future-ready** — the manager scales to hundreds of engines without redesign. New engines can be added without modifying existing ones.

### 17.2 Lifecycle States

```
Registered → Loaded → Initialized → Ready → Running → Completed
                                              ↘ Failed
```

The `EngineState` enum defines these states, and the `EngineStateTransition` class validates that transitions are legal (no skipping states, no going back except to `Failed`).

### 17.3 Manager vs Registry

The manager is deliberately separate from the `EngineRegistry`:

- **EngineRegistry** — a "dumb catalogue" that stores engine instances and provides lookup by name. It enforces no policy.
- **CoreEngineManager** — the "executive brain" that adds the lifecycle, dependency, queue, security, and logging layers on top of the registry.

The manager *uses* the registry for lookup but adds all the policy enforcement.

### 17.4 Manager Sub-Modules

| File | Responsibility |
|------|----------------|
| `engine_manager.py` | `CoreEngineManager` — the main manager class |
| `engine_entry.py` | `EngineEntry`, `EngineMetadata` — managed engine records |
| `execution_queue.py` | `ExecutionQueue`, `QueueItem` — execution ordering |
| `lifecycle.py` | `EngineState`, `EngineStateTransition` — lifecycle states and transitions |
| `errors.py` | `DependencyError`, `DuplicateEngineError`, `LifecycleError`, `ManagerError`, `SecurityError`, `UnknownEngineError` |

### 17.5 ManagerResult

The `ManagerResult` is the outcome of a full managed run:

- `success: bool` — whether every engine completed successfully.
- `engine_results: List[StageResult]` — per-engine results in execution order.
- `errors: List[str]` — aggregated error messages.
- `failed_engine_id: str` — the ID of the first engine that failed (if any).
- `failure_stage: str` — the lifecycle stage at which the failure occurred.
- `total_duration_s: float` — total wall-clock duration.
- `metadata: Dict[str, Any]` — extra diagnostic information.

---

## 18. Test Suite Summary

### 18.1 Test Files

| Test File | Lines | Engine Tested |
|-----------|-------|---------------|
| `tests/test_blueprint_validator.py` | 1,504 | Blueprint Validator Engine |
| `tests/test_dependency_resolver.py` | 2,524 | Dependency Resolution Engine |
| `tests/test_file_planner.py` | 2,216 | File Generation Planning Engine |
| `tests/test_manager.py` | 412 | Core Engine Manager |
| `tests/test_project_context.py` | 2,870 | Project Context Engine |
| `tests/test_project_planner.py` | 1,215 | Project Planning Engine |
| `tests/test_structure_generator.py` | 1,299 | Structure Generation Engine |
| `tests/test_visual_page_reconstruction.py` | 1,482 | Visual Page Reconstruction Engine |
| `tests/test_intelligence_graph.py` | 3,318 | Project Intelligence Graph Engine |
| **Total** | **16,840** | **9 test files** |

### 18.2 Test Coverage

- **Blueprint Validator:** Tests cover all 6 validation layers, conflict detection, quality scoring, approval/rejection logic, and edge cases (empty blueprint, missing fields, conflicting features).
- **Dependency Resolver:** Tests cover all 11 steps, component analysis, library determination, dependency graph building, compatibility checking, conflict detection, optimization, security checking, and plan validation.
- **File Planner:** Tests cover all 9 steps, component analysis, file determination, relationship resolution, generation order computation, conflict detection, and plan validation.
- **Core Engine Manager:** Tests cover registration, lifecycle states, dependency validation, execution queue, error management, and security rules.
- **Project Context:** 125 tests covering all data classes, all 6 readers, the context assembler, the context linker (12 O(1) indices), the context validator, and the main engine. All 125 tests pass.
- **Project Planner:** Tests cover all 10 internal steps, feature breakdown, component building, relationship building, dependency graph, execution plan, risk detection, and validation.
- **Structure Generator:** Tests cover all 8 steps, folder planning, file planning, naming, build order computation, and structure validation.
- **Visual Page Reconstruction:** Tests cover all 4 phases, page analysis, image extraction, layout rebuilding, choice detection, coordinate mapping, and visual validation (95% threshold).
- **Project Intelligence Graph:** 127 tests covering all data classes (GraphNode, GraphEdge, GraphFinding, GraphIndices, GraphProvenance, ProjectIntelligenceGraph), all 19 node-type constants, all 12 edge-kind constants, all 7 source-artefact constants, all 7 category constants, the graph builder (7 artefact → nodes + edges), the graph navigator (11 O(1) indices), the circular detector (3-colour DFS, cycle normalisation, broken references, unused components, orphan files, dead components), the graph validator (9 consistency checks), the main engine (type-checking, output verification), graph integrity, bootstrap registration, serialisation, and end-to-end integration. All 127 tests pass.

---

## 19. Technology Stack

### 19.1 Programming Language

- **Python 3.11** — the entire system is written in Python 3.11 using modern features: dataclasses, type hints, `from __future__ import annotations`, `Optional`, `Dict`, `List`, `Any`, `field(default_factory=...)`.

### 19.2 Libraries and Frameworks

| Library | Purpose | Used By |
|---------|---------|---------|
| `pdfplumber` | PDF parsing and element extraction | Visual Page Reconstruction Engine |
| `python-telegram-bot>=20.7` | The Telegram bot framework (generated projects use this) | Blueprint Composer, Project Planner |
| `SQLAlchemy>=2.0` | Database ORM (generated projects use this) | Blueprint Composer, Project Planner |
| `openai>=1.0` | AI integration (generated projects use this) | Blueprint Composer |
| `yt-dlp` | Media downloading (generated projects use this) | Blueprint Composer |
| `stripe` | Payment processing (generated projects use this) | Blueprint Composer |

### 19.3 Design Patterns and Techniques

| Pattern | Usage |
|---------|-------|
| **Pipeline Architecture** | The entire system is a linear pipeline with fail-fast semantics. |
| **Strategy Pattern** | Bot-type profiles in the Blueprint Composer; each profile is a function dispatched by bot type. |
| **Template Method** | `BaseEngine` provides the template; concrete engines implement `execute()`. |
| **Separation of Concerns** | Each engine has a single, well-defined responsibility. No engine does work outside its scope. |
| **Artefact-Based Communication** | Engines communicate through artefacts in the `GenerationContext`, never directly. |
| **Dataclass-Based Data Models** | All data models use Python dataclasses with `field(default_factory=...)`. |
| **O(1) Look-up Indices** | The Project Context Engine precomputes 12 O(1) look-up indices; the Intelligence Graph Engine precomputes 11 O(1) look-up indices for fast graph traversal. |
| **Graph-Based Architecture** | The Intelligence Graph Engine converts all 7 artefacts into a single typed graph with 19 node types and 12 edge kinds, enabling O(1) look-up and multi-hop navigation. |
| **Three-Colour DFS** | The Circular Detector uses a WHITE/GREY/BLACK DFS with recursion stack to detect cycles in O(V+E) time. |
| **Cycle Normalisation** | Circular dependencies are normalised by rotating the cycle so the lexicographically smallest node ID is first, preventing duplicate cycle reports. |
| **Topological Sorting** | Used for build order computation (Component Detector), generation order (File Planner), and load order (Dependency Resolver). |
| **Layered Validation** | The Blueprint Validator uses 6 independent validation layers. |
| **Multi-Stage Analysis** | The Analyzer uses 10 sequential stages with shared mutable state. |
| **Provenance Tracking** | The Project Context Engine records the source artefact for every piece of information. |
| **Dependency Injection** | The bootstrap function wires all engines, builders, validators, and the manager together. |
| **Registry Pattern** | The `EngineRegistry` is a dumb catalogue; the `CoreEngineManager` adds policy on top. |
| **Rule-Based Heuristics** | The Intent Parser uses keyword-matching rules for bot type classification and feature detection. |
| **Arabic-English Transliteration** | The `_slugify()` function transliterates Arabic text to English slugs for package names. |
| **Conditional Imports** | The Visual Page Reconstruction Engine conditionally imports `pdfplumber`. |

### 19.4 Error Handling

- Every engine's `execute()` method returns a `StageResult` with `success`, `errors`, and `warnings`.
- The pipeline is **fail-fast**: the first failing engine stops the entire pipeline.
- The `CoreEngineManager` logs every error, the engine name, and the failure stage.
- Each engine performs type-checking on its input artefacts and returns a `failed` result with a descriptive error message if an artefact is missing or has the wrong type.
- Each engine distinguishes between **errors** (stop the pipeline) and **warnings** (continue but log).

### 19.5 Logging

The system uses a custom logging module (`telegram_bot_engine/logging/logger.py`) with the `get_logger(name)` function. Every engine gets its own logger via `self._log = get_logger(f"engine.{name}")`. The logging is structured with metadata dictionaries:

```python
self._log.info("Starting analysis", {"request_length": len(raw_request)})
self._log.info("Analysis complete", {
    "bot_type": report.primary_bot_type.type,
    "features": len(report.features),
    "ready": report.ready,
})
```

---

## 20. Design Principles

### 20.1 Single Responsibility

Every engine has exactly one responsibility. The analyzer analyses, the planner plans, the validator validates, the structure generator builds structure, the component detector detects components, and so on. No engine performs work outside its designated scope.

### 20.2 No Direct Communication

No engine ever accesses another engine directly. All communication flows through the `GenerationContext.artefacts` dictionary and the `CoreEngineManager`. This keeps the pipeline decoupled and testable.

### 20.3 Forbidden from Reading the Raw Request

With the exception of the Analyzer and Intent Parser (the first two engines in the understanding phase), no engine is allowed to read the user's raw request. Every engine reads only the artefacts produced by upstream engines. This ensures that the analysis is done once, authoritatively, and all downstream engines work from the same data.

### 20.4 No Code Generation Before Planning

No engine writes code, creates files, or builds anything on disk until the entire planning and validation phase is complete. The first 8 engines (1–8) produce only data models and plans. Only after the blueprint is validated, the structure is planned, components are detected, files are planned, and dependencies are resolved does the system have enough information to start generating code.

### 20.5 Traceability

Every piece of information in the `ProjectContext` records its source artefact. The `SourceProvenance` mapping allows any downstream engine to trace any piece of information back to the artefact that produced it.

### 20.6 Fail-Fast

The pipeline stops on the first failing engine. No downstream engine runs if an upstream engine has failed. This prevents cascading errors and makes debugging easier.

### 20.7 Deterministic Execution Order

The execution order is determined by the `CoreEngineManager` based on priorities and dependencies. No engine can change its own order. The order is deterministic and reproducible.

### 20.8 Read-Only for Downstream

The `ProjectContext` is read-only for all downstream engines — no engine may modify it directly. Any modification requires a dedicated engine.

### 20.9 Scalability

The system scales to hundreds of engines without redesign. New engines can be added by creating a new engine class, registering it in `bootstrap.py`, and adding a new test file — no existing code needs to change.

### 20.10 Testability

Every engine is independently testable. Each engine's `execute()` method takes a `GenerationContext` with pre-populated artefacts and returns a `StageResult`. Tests can construct a context with mock artefacts and verify the engine's output without running the entire pipeline.

### 20.11 Arabic Language Support

The system fully supports Arabic-language requests. The Intent Parser detects Arabic text and classifies bot types using Arabic keywords. The Blueprint Composer transliterates Arabic text to English slugs for package names. The system handles both Arabic and English seamlessly.

---

## 21. Project Statistics

### 21.1 Code Statistics

| Metric | Value |
|--------|-------|
| **Total source files** | 151 Python files |
| **Total source lines** | 36,404 lines |
| **Total test files** | 9 test files |
| **Total test lines** | 16,840 lines |
| **Total files (source + test)** | 160 files |
| **Total lines (source + test)** | 53,244 lines |
| **Number of engines** | 12 |
| **Number of execution phases** | 8 |

### 21.2 Per-Engine Statistics

| Engine | ID | Priority | Files | Lines | Output Artefact |
|--------|----|----------|-------|-------|-----------------|
| Core Request Analyzer | `analyzer` | 10 | 14 | 2,642 | `analysis_report` |
| Intent Parser | `intent_parser` | 20 | 1 | 121 | `intent` |
| Blueprint Composer | `blueprint_composer` | 30 | 1 | 327 | `blueprint` |
| Project Planner | `project_planner` | 40 | 8 | 2,405 | `project_blueprint` |
| Blueprint Validator | `blueprint_validator` | 50 | 12 | 2,494 | `blueprint_validation_report` |
| Structure Generator | `structure_generator` | 60 | 7 | 2,453 | `project_structure_map` |
| Component Detector | `component_detector` | 70 | 11 | 2,841 | `component_registry` |
| File Planner | `file_planner` | 80 | 9 | 2,638 | `file_generation_plan` |
| Visual Page Reconstruction | `visual_page_reconstruction` | 90 | 9 | 3,284 | `page_analyses`, `rebuilt_pdf_bytes`, `visual_similarity_reports` |
| Dependency Resolver | `dependency_resolver` | 95 | 11 | 4,248 | `dependency_resolution_report` |
| Project Context | `project_context` | 96 | 12 | 3,663 | `project_context` |
| Intelligence Graph | `intelligence_graph` | 97 | 7 | 4,002 | `intelligence_graph` |
| **Total** | | | **102** | **28,118** | |

### 21.3 Data Model Class Count

| Engine | Data Classes |
|--------|-------------|
| Analyzer | `Token`, `KeywordMatch`, `BotTypeEntry`, `Feature`, `Technology`, `Relationship`, `Conflict`, `MissingInfo`, `ConfidenceScore`, `AnalysisReport` (10) |
| Project Planner | `ProjectIdentity`, `StructureEntry`, `ExpectedStructure`, `InternalComponent`, `ComponentRelationship`, `RequiredEngine`, `BlueprintRisk`, `BlueprintValidation`, `ProjectBlueprint` (9) |
| Blueprint Validator | `ValidationFinding`, `LayerResult`, `QualityScore`, `ConflictFinding`, `MissingInformationFinding`, `BlueprintValidationReport` (6) |
| Structure Generator | `FolderEntry`, `FileEntry`, `StructureRelationship`, `BuildOrderEntry`, `ProjectStructureMap` (5) |
| Component Detector | `DetectedComponent`, `ComponentDependencyEdge`, `ComponentBuildOrderEntry`, `DetectionFinding`, `ComponentRegistry` (5) |
| File Planner | `FilePlanEntry`, `FileRelationship`, `FileGenerationOrderEntry`, `PlanFinding`, `FileGenerationPlan` (5) |
| Dependency Resolver | `DependencyEntry`, `DependencyRelationship`, `DependencyOrderEntry`, `ResolutionFinding`, `DependencyResolutionReport` (5) |
| Visual Page Reconstruction | `PageAnalysis`, `PageDimensions`, `PageImage`, `PageText`, `PageChoice`, `PageTable`, `PageEquation`, `PageSeparator`, `ElementPosition`, `VisualLayer` (10) |
| Project Context | `ProjectGoal`, `FeatureSummary`, `ComponentSummary`, `FileSummary`, `DependencySummary`, `RelationshipSummary`, `ExecutionStage`, `ContextLink`, `ExpansionPoint`, `ContextFinding`, `LinkIndices`, `SourceProvenance`, `ProjectContext` (13) |
| Intelligence Graph | `GraphNode`, `GraphEdge`, `GraphFinding`, `GraphIndices`, `GraphProvenance`, `ProjectIntelligenceGraph` (6) |

---

## Document Information

- **Project:** Telegram Bot Generation Engine (`ai_Agent_7h_bot`)
- **Repository:** `https://github.com/atemmokhtar2-blip/ai_Agent_7h_bot`
- **Total Engines:** 12
- **Total Source Files:** 151 (36,404 lines)
- **Total Test Files:** 9 (16,840 lines)
- **Total Codebase:** 160 files, 53,244 lines
- **Language:** Python 3.11
- **Architecture:** Modular pipeline with artefact-based communication and graph-based intelligence

---

*This documentation was generated from the actual source code. Every detail has been verified against the implementation. All engine classes, method signatures, data models, constants, and architectural decisions are documented as they exist in the codebase.*
