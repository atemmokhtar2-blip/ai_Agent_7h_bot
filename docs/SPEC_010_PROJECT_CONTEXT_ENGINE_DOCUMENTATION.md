# Specification 010 — Project Context Engine
## Complete Technical Documentation

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [File Inventory](#3-file-inventory)
4. [Data Model (context_data.py)](#4-data-model-context_datapy)
5. [Readers](#5-readers)
6. [Context Assembler](#6-context-assembler)
7. [Context Linker](#7-context-linker)
8. [Context Validator](#8-context-validator)
9. [Project Context Engine](#9-project-context-engine)
10. [Package Exports (__init__.py)](#10-package-exports-__init__py)
11. [Integration](#11-integration)
12. [Test Suite](#12-test-suite)
13. [Constants Reference](#13-constants-reference)
14. [Data Flow Diagram](#14-data-flow-diagram)
15. [Design Principles](#15-design-principles)

---

## 1. Overview

### 1.1 Purpose

The Project Context Engine builds a complete, authoritative, unified understanding of the entire project by merging six upstream artefacts into a single unified model called `ProjectContext`. It does **not** write code, create files, or make build decisions. Its sole function is to produce the single authoritative context that every downstream engine can query for any piece of project information.

### 1.2 Data Source

The engine reads **only** six artefacts from the generation context:

| # | Artefact Key | Type | Produced By |
|---|---|---|---|
| 1 | `project_blueprint` | `ProjectBlueprint` | Project Planning Engine |
| 2 | `blueprint_validation_report` | `BlueprintValidationReport` | Blueprint Validator Engine |
| 3 | `project_structure_map` | `ProjectStructureMap` | Structure Generation Engine |
| 4 | `component_registry` | `ComponentRegistry` | Component Detection Engine |
| 5 | `file_generation_plan` | `FileGenerationPlan` | File Generation Planning Engine |
| 6 | `dependency_resolution_report` | `DependencyResolutionReport` | Dependency Resolution Engine |

The engine is **forbidden** from reading the user's request.

### 1.3 Output

The final output is a `ProjectContext` object, stored in the generation context as the `project_context` artefact and also in `context.metadata["project_context"]`.

### 1.4 Location

All source files reside in:
```
telegram_bot_engine/engines/generators/project_context/
```

Total: 12 Python files, 3,663 lines of source code.

---

## 2. Architecture

### 2.1 Pipeline Position

The Project Context Engine sits at priority **96** in the pipeline, directly after the Dependency Resolution Engine (priority 95). It depends on `dependency_resolver`, which transitively depends on all upstream engines.

```
analyzer (10) → intent_parser (20) → blueprint_composer (30)
→ project_planner (40) → blueprint_validator (50)
→ structure_generator (60) → component_detector (70)
→ file_planner (80) → visual_page_reconstruction (90)
→ dependency_resolver (95) → project_context (96)
```

### 2.2 Internal Structure

The engine is composed of four layers:

1. **Readers** (6 classes) — each reads one upstream artefact and extracts context-relevant data into plain containers.
2. **ContextAssembler** — merges the output of all six readers into a unified `ProjectContext`.
3. **ContextLinker** — builds precomputed O(1) look-up indices and the context graph edges.
4. **ContextValidator** — validates the assembled context for internal consistency.

The main engine class (`ProjectContextEngine`) orchestrates these four layers in sequence.

### 2.3 Engine Contract

The engine inherits from `BaseEngine` (which inherits from `Engine(ABC, Component)`) and implements:

```python
def execute(self, context: GenerationContext) -> StageResult:
```

It uses `self.ok(outputs=..., metadata=...)` for success and `self.failed(errors=..., outputs=..., warnings=...)` for failure.

### 2.4 Constructor Configuration

```python
def __init__(self) -> None:
    super().__init__(
        name="project_context",
        version="1.0.0",
        description=(
            "Builds the complete, unified project context by "
            "merging the Project Blueprint, Blueprint "
            "Validation Report, Project Structure Map, "
            "Component Registry, File Generation Plan, and "
            "Dependency Resolution Report.  Produces a "
            "Project Context artefact with precomputed O(1) "
            "look-up indices.  Does not write code, create "
            "files, or make build decisions."
        ),
        tags=["generation", "context", "merging"],
        metadata={"phase": "build_context"},
    )
    self._assembler = ContextAssembler()
    self._linker = ContextLinker()
    self._validator = ContextValidator()
```

---

## 3. File Inventory

| File | Lines | Bytes | Purpose |
|------|-------|-------|---------|
| `context_data.py` | 1,057 | 39,895 | Main data model — all dataclasses and constants |
| `blueprint_reader.py` | 217 | 7,929 | Reads `ProjectBlueprint` |
| `validation_reader.py` | 159 | 5,713 | Reads `BlueprintValidationReport` |
| `structure_reader.py` | 152 | 5,426 | Reads `ProjectStructureMap` |
| `registry_reader.py` | 141 | 4,908 | Reads `ComponentRegistry` |
| `file_plan_reader.py` | 142 | 4,921 | Reads `FileGenerationPlan` |
| `dependency_reader.py` | 145 | 4,978 | Reads `DependencyResolutionReport` |
| `context_assembler.py` | 443 | 16,341 | Merges all six readers' output |
| `context_linker.py` | 302 | 11,071 | Builds O(1) link indices and context graph |
| `context_validator.py` | 360 | 13,791 | Validates context for internal consistency |
| `project_context_engine.py` | 414 | 16,728 | Main engine class — orchestrates all steps |
| `__init__.py` | 131 | 3,959 | Package exports |
| **Total** | **3,663** | **131,460** | |

---

## 4. Data Model (context_data.py)

### 4.1 Constants

#### 4.1.1 Source-Arteact Constants

These constants identify which upstream artefact a piece of data came from. Every sub-model in the Project Context records its source using one of these constants.

| Constant | Value | Description |
|----------|-------|-------------|
| `SOURCE_BLUEPRINT` | `"blueprint"` | From the project blueprint |
| `SOURCE_VALIDATION` | `"validation"` | From the blueprint validation report |
| `SOURCE_STRUCTURE` | `"structure"` | From the project structure map |
| `SOURCE_COMPONENT_REGISTRY` | `"component_registry"` | From the component registry |
| `SOURCE_FILE_PLAN` | `"file_plan"` | From the file generation plan |
| `SOURCE_DEPENDENCY_REPORT` | `"dependency_report"` | From the dependency resolution report |
| `ALL_SOURCES` | tuple of all 6 | All source identifiers |

#### 4.1.2 Severity Constants

| Constant | Value |
|----------|-------|
| `SEVERITY_ERROR` | `"error"` |
| `SEVERITY_WARNING` | `"warning"` |
| `SEVERITY_INFO` | `"info"` |
| `ALL_SEVERITIES` | tuple of all 3 |

#### 4.1.3 Link-Kind Constants

These constants describe the type of edge in the context graph.

| Constant | Value | Description |
|----------|-------|-------------|
| `LINK_FEATURE_TO_COMPONENT` | `"feature_to_component"` | Feature → implementing component |
| `LINK_COMPONENT_TO_FILE` | `"component_to_file"` | Component → containing file |
| `LINK_FILE_TO_DEPENDENCY` | `"file_to_dependency"` | File → required dependency |
| `LINK_DEPENDENCY_TO_STAGE` | `"dependency_to_stage"` | Dependency → execution stage |
| `LINK_COMPONENT_TO_STAGE` | `"component_to_stage"` | Component → execution stage |
| `LINK_FEATURE_TO_STAGE` | `"feature_to_stage"` | Feature → execution stage |
| `ALL_LINK_KINDS` | tuple of all 6 | All link kinds |

---

### 4.2 Dataclasses

#### 4.2.1 ProjectGoal

The high-level goal and identity of the project, derived from the `ProjectBlueprint`'s identity section.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `""` | Machine-friendly project name (slug) |
| `display_name` | `str` | `""` | Human-readable project name |
| `bot_type` | `str` | `"general"` | Detected bot type |
| `primary_goal` | `str` | `""` | One-sentence description |
| `language` | `str` | `"python"` | Programming language |
| `language_version` | `str` | `"3.11"` | Language version |
| `framework` | `str` | `"python-telegram-bot"` | Telegram bot framework |
| `database` | `str` | `""` | Database backend (empty if none) |
| `source_artefact` | `str` | `SOURCE_BLUEPRINT` | Source artefact |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.2 FeatureSummary

A single feature in the project context, derived from a `FeatureUnit` in the blueprint.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | (required) | Feature name (machine-friendly) |
| `display_name` | `str` | `""` | Human-readable feature name |
| `description` | `str` | `""` | What the feature does |
| `priority` | `int` | `100` | Feature priority (lower = built first) |
| `source_feature` | `str` | `""` | Source feature unit name |
| `components` | `List[str]` | `[]` | Component names implementing this feature |
| `source_artefact` | `str` | `SOURCE_BLUEPRINT` | Source artefact |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.3 ComponentSummary

A single detected component, derived from a `DetectedComponent` in the component registry.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | (required) | Component name (unique) |
| `type` | `str` | `"utility"` | Component type |
| `purpose` | `str` | `""` | Short description |
| `responsibility` | `str` | `""` | Single, clear responsibility |
| `source_feature` | `str` | `""` | Feature this component belongs to |
| `location` | `str` | `""` | Relative path |
| `build_order` | `int` | `100` | Build sequence position |
| `importance` | `str` | `"normal"` | Importance level |
| `files` | `List[str]` | `[]` | File paths implementing this component |
| `dependencies` | `List[str]` | `[]` | Dependency names required |
| `depends_on` | `List[str]` | `[]` | Other components this depends on |
| `depended_by` | `List[str]` | `[]` | Components that depend on this |
| `source_artefact` | `str` | `SOURCE_COMPONENT_REGISTRY` | Source artefact |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.4 FileSummary

A single planned file, derived from a `FilePlanEntry` from the file generation plan.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | (required) | File name (e.g. `"main.py"`) |
| `path` | `str` | (required) | Full relative path from project root |
| `file_type` | `str` | `"text"` | File type |
| `purpose` | `str` | `""` | What this file is for |
| `folder` | `str` | `""` | Folder path |
| `responsible_engine` | `str` | `""` | Engine that builds this file |
| `generation_priority` | `int` | `20` | Broad generation phase |
| `build_order` | `int` | `0` | Precise generation position |
| `source_component` | `str` | `""` | Component this file belongs to |
| `depends_on` | `List[str]` | `[]` | Other files this depends on |
| `depended_by` | `List[str]` | `[]` | Files that depend on this |
| `reason_for_existence` | `str` | `""` | Why this file exists |
| `contains_code` | `bool` | `False` | Whether this file contains executable code |
| `source_artefact` | `str` | `SOURCE_FILE_PLAN` | Source artefact |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.5 DependencySummary

A single resolved dependency, derived from a `DependencyEntry` from the dependency resolution report.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | (required) | Dependency name |
| `type` | `str` | `"library"` | Dependency type |
| `suggested_version` | `str` | `"latest"` | Suggested version |
| `version_constraint` | `str` | `""` | Version constraint |
| `reason` | `str` | `""` | Why this dependency is needed |
| `source_components` | `List[str]` | `[]` | Components requiring this dependency |
| `priority` | `int` | `20` | Broad resolution phase |
| `load_order` | `int` | `0` | Load sequence position |
| `language` | `str` | `""` | Programming language |
| `framework` | `str` | `""` | Framework |
| `depends_on` | `List[str]` | `[]` | Other dependencies this depends on |
| `depended_by` | `List[str]` | `[]` | Dependencies that depend on this |
| `source_artefact` | `str` | `SOURCE_DEPENDENCY_REPORT` | Source artefact |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.6 RelationshipSummary

A single relationship, normalised from all upstream artefacts (blueprint, structure, file plan, dependency, registry relationships).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | `str` | (required) | Source element name |
| `target` | `str` | (required) | Target element name |
| `kind` | `str` | `"depends_on"` | Relationship kind |
| `description` | `str` | `""` | Human-readable description |
| `source_artefact` | `str` | `SOURCE_BLUEPRINT` | Source artefact |

Methods: `to_dict() -> Dict[str, Any]`

Relationship kinds include: `"depends_on"`, `"uses"`, `"calls"`, `"managed_by"`, `"stored_in"`, `"contains"`, `"imports"`, `"configures"`, `"documents"`, `"tested_by"`, `"requires"`, `"extends"`, `"conflicts_with"`, `"replaces"`.

#### 4.2.7 ExecutionStage

A single execution stage, derived from the blueprint's execution plan and enriched with components, files, and dependencies.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | (required) | Stage name |
| `phase` | `int` | `0` | Phase number (0-based) |
| `priority` | `int` | `100` | Broad priority (lower = first) |
| `components` | `List[str]` | `[]` | Component names in this stage |
| `files` | `List[str]` | `[]` | File paths in this stage |
| `dependencies` | `List[str]` | `[]` | Dependency names in this stage |
| `source_artefact` | `str` | `SOURCE_BLUEPRINT` | Source artefact |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.8 ContextLink

A single link (edge) in the context graph, precomputed by the `ContextLinker`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | `str` | (required) | Source element name |
| `target` | `str` | (required) | Target element name |
| `kind` | `str` | `LINK_FEATURE_TO_COMPONENT` | Link kind (one of `LINK_*` constants) |
| `source_artefact` | `str` | `SOURCE_BLUEPRINT` | Source artefact |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.9 ExpansionPoint

A future expansion point in the project, derived from scalability flags on components, files, and directories.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `area` | `str` | (required) | Area that can be expanded |
| `description` | `str` | `""` | How the area can be expanded |
| `source_artefact` | `str` | `SOURCE_BLUEPRINT` | Source artefact |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.10 ContextFinding

A single finding produced during context building or validation.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `severity` | `str` | `SEVERITY_WARNING` | `"error"`, `"warning"`, or `"info"` |
| `code` | `str` | `""` | Machine-readable code |
| `message` | `str` | `""` | Human-readable description |
| `affected` | `str` | `""` | Name of the affected element |
| `resolution_hint` | `str` | `""` | Suggestion on how to fix |
| `category` | `str` | `"validation"` | Finding category |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.11 LinkIndices

Precomputed look-up indices for O(1) context graph traversal, built by the `ContextLinker`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `feature_to_components` | `Dict[str, List[str]]` | `{}` | Feature name → component names |
| `component_to_features` | `Dict[str, List[str]]` | `{}` | Component name → feature names |
| `component_to_files` | `Dict[str, List[str]]` | `{}` | Component name → file paths |
| `file_to_components` | `Dict[str, List[str]]` | `{}` | File path → component names |
| `file_to_dependencies` | `Dict[str, List[str]]` | `{}` | File path → dependency names |
| `dependency_to_files` | `Dict[str, List[str]]` | `{}` | Dependency name → file paths |
| `dependency_to_components` | `Dict[str, List[str]]` | `{}` | Dependency name → component names |
| `component_to_dependencies` | `Dict[str, List[str]]` | `{}` | Component name → dependency names |
| `component_to_stage` | `Dict[str, str]` | `{}` | Component name → stage name |
| `feature_to_stage` | `Dict[str, str]` | `{}` | Feature name → stage name |
| `file_to_stage` | `Dict[str, str]` | `{}` | File path → stage name |
| `dependency_to_stage` | `Dict[str, str]` | `{}` | Dependency name → stage name |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.12 SourceProvenance

Records which upstream artefacts were used to build the context (the traceability record).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `blueprint_name` | `str` | `""` | Name of the blueprint used |
| `validation_status` | `str` | `""` | Approval status of the blueprint |
| `structure_map_name` | `str` | `""` | Name of the structure map used |
| `component_registry_name` | `str` | `""` | Name of the component registry used |
| `file_plan_name` | `str` | `""` | Name of the file generation plan used |
| `dependency_report_name` | `str` | `""` | Name of the dependency resolution report used |
| `all_sources_used` | `List[str]` | `[]` | All source artefact identifiers |

Methods: `to_dict() -> Dict[str, Any]`

#### 4.2.13 ProjectContext

The complete, authoritative, unified understanding of the project. This is the **only** object the Project Context Engine produces. It is stored in the generation context as the `project_context` artefact.

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `goal` | `ProjectGoal` | `ProjectGoal()` | High-level project identity |
| `features` | `List[FeatureSummary]` | `[]` | All features |
| `components` | `List[ComponentSummary]` | `[]` | All components |
| `files` | `List[FileSummary]` | `[]` | All files |
| `dependencies` | `List[DependencySummary]` | `[]` | All dependencies |
| `relationships` | `List[RelationshipSummary]` | `[]` | All relationships (normalised, deduplicated) |
| `stages` | `List[ExecutionStage]` | `[]` | All execution stages |
| `links` | `List[ContextLink]` | `[]` | Context graph edges |
| `indices` | `LinkIndices` | `LinkIndices()` | Precomputed O(1) look-up tables |
| `expansion_points` | `List[ExpansionPoint]` | `[]` | Future expansion points |
| `provenance` | `SourceProvenance` | `SourceProvenance()` | Traceability record |
| `findings` | `List[ContextFinding]` | `[]` | Findings from building and validation |
| `summary` | `str` | `""` | Human-readable summary |
| `notes` | `List[str]` | `[]` | General notes |
| `warnings` | `List[str]` | `[]` | Warnings from context building |

**Convenience Properties (read-only):**

| Property | Type | Description |
|----------|------|-------------|
| `feature_count` | `int` | `len(self.features)` |
| `component_count` | `int` | `len(self.components)` |
| `file_count` | `int` | `len(self.files)` |
| `dependency_count` | `int` | `len(self.dependencies)` |
| `relationship_count` | `int` | `len(self.relationships)` |
| `stage_count` | `int` | `len(self.stages)` |
| `link_count` | `int` | `len(self.links)` |
| `is_empty` | `bool` | True if no features, components, files, or dependencies |
| `has_errors` | `bool` | True if any finding has `SEVERITY_ERROR` |
| `error_count` | `int` | Count of `SEVERITY_ERROR` findings |
| `warning_count` | `int` | Count of `SEVERITY_WARNING` findings |

**Look-up Methods (O(n) linear scan):**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_feature(name)` | `Optional[FeatureSummary]` | Find feature by name |
| `get_component(name)` | `Optional[ComponentSummary]` | Find component by name |
| `get_file(path)` | `Optional[FileSummary]` | Find file by path |
| `get_dependency(name)` | `Optional[DependencySummary]` | Find dependency by name |
| `get_stage(name)` | `Optional[ExecutionStage]` | Find stage by name |

**O(1) Index-Based Look-up Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `components_for_feature(feature_name)` | `List[str]` | Components implementing a feature |
| `features_for_component(component_name)` | `List[str]` | Features a component belongs to |
| `files_for_component(component_name)` | `List[str]` | Files implementing a component |
| `components_for_file(file_path)` | `List[str]` | Components a file belongs to |
| `dependencies_for_file(file_path)` | `List[str]` | Dependencies a file requires |
| `files_for_dependency(dependency_name)` | `List[str]` | Files requiring a dependency |
| `components_for_dependency(dependency_name)` | `List[str]` | Components requiring a dependency |
| `dependencies_for_component(component_name)` | `List[str]` | Dependencies a component requires |
| `stage_for_component(component_name)` | `str` | Stage name for a component |
| `stage_for_feature(feature_name)` | `str` | Stage name for a feature |
| `stage_for_file(file_path)` | `str` | Stage name for a file |
| `stage_for_dependency(dependency_name)` | `str` | Stage name for a dependency |

**Finding Management:**

| Method | Description |
|--------|-------------|
| `add_finding(severity, code, message, affected, resolution_hint, category)` | Appends a `ContextFinding` and adds warning messages to `self.warnings` if severity is `SEVERITY_WARNING` |

**Serialisation:**

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `Dict[str, Any]` | Full serialisation including all sub-objects, counts, and metadata |

The `to_dict()` output includes: `goal`, all count properties (`feature_count`, `component_count`, `file_count`, `dependency_count`, `relationship_count`, `stage_count`, `link_count`, `error_count`, `warning_count`), `summary`, `notes`, `warnings`, and the full lists of `features`, `components`, `files`, `dependencies`, `relationships`, `stages`, `links`, `indices`, `expansion_points`, `provenance`, and `findings` — each serialised via their own `to_dict()`.

---

## 5. Readers

All six readers follow the same pattern: they are **stateless** classes with a single `read()` method that takes the upstream artefact and returns a dict of plain data containers.

### 5.1 BlueprintReader

**File:** `blueprint_reader.py` (217 lines, 7,929 bytes)

**Class:** `BlueprintReader`

**Method:** `read(blueprint: ProjectBlueprint) -> Dict[str, Any]`

**Returns a dict with keys:**
- `goal` — a `ProjectGoal`
- `features` — a list of `FeatureSummary`
- `relationships` — a list of `RelationshipSummary`
- `stages` — a list of `ExecutionStage`
- `expansion_points` — a list of `ExpansionPoint`

**Internal methods:**

1. **`_read_goal(blueprint)`** — Extracts the project identity from `blueprint.identity`. Builds a `primary_goal` string based on the bot type and feature count.

2. **`_read_features(blueprint)`** — Iterates `blueprint.features` (each a `FeatureUnit`), creating a `FeatureSummary` for each with:
   - `name` from `fu.name`
   - `display_name` from `fu.display_name` or `fu.name`
   - `description` from `fu.description`
   - `priority` from `fu.build_priority`
   - `source_feature` from `fu.source_feature` or `fu.name`
   - `components` from `fu.introduces_components`

3. **`_read_relationships(blueprint)`** — Iterates `blueprint.relationships` (each a `ComponentRelationship`), creating a `RelationshipSummary` for each with `source`, `target`, `kind`, `description` from the relationship.

4. **`_read_stages(blueprint)`** — Iterates `blueprint.execution_plan.phases` (each an `ExecutionPhase`), creating an `ExecutionStage` for each with:
   - `name` from `phase.name`
   - `phase` from `phase.number`
   - `priority` from `phase.number * 100`
   - `components` from `phase.components`
   - `files` and `dependencies` initially empty (enriched later by the assembler)

5. **`_read_expansion_points(blueprint)`** — Collects expansion points from two sources:
   - Directory structure entries (`blueprint.structure.entries` where `kind == "directory"`)
   - Feature components (`blueprint.components` where `kind == "feature"`)
   - Deduplicates by area using a `seen` set.

**Imports from upstream modules:**
```python
from ..project_planner.blueprint import (
    ProjectBlueprint, InternalComponent, ComponentRelationship,
)
from ..project_planner.feature_unit import FeatureUnit
from ..project_planner.execution_plan import ExecutionPlan, ExecutionPhase
```

---

### 5.2 ValidationReader

**File:** `validation_reader.py` (159 lines, 5,713 bytes)

**Class:** `ValidationReader`

**Method:** `read(report: BlueprintValidationReport) -> Dict[str, Any]`

**Returns a dict with keys:**
- `validation_status` — the approval status string
- `quality_scores` — a dict of quality sub-scores
- `overall_quality` — the overall quality score (float)
- `findings` — a list of `ContextFinding` objects
- `provenance_partial` — `{"validation_status": report.status}`

**Internal methods:**

1. **`_extract_quality_scores(report)`** — Returns a dict with `structure_quality`, `dependency_quality`, `feature_quality`, `planning_quality`, `overall`, `minimum_required` from `report.quality`. Returns empty dict if `report.quality` is `None`.

2. **`_extract_findings(report)`** — Collects findings from five sources:
   - **Layer results:** `report.layers.items()` → each layer's findings (with `category="validation"`)
   - **Conflicts:** `report.conflicts` → each conflict (with `code="conflict"`, `category="consistency"`)
   - **Errors:** `report.errors` → each error (with `category="validation"`, uses `hasattr` checks for flexible error objects)
   - **Warnings:** `report.warnings` → each warning (with `category="validation"`, uses `hasattr` checks)
   - **Missing info:** `report.missing_info` → each missing item (with `code="missing_information"`, severity is `SEVERITY_ERROR` if required, else `SEVERITY_WARNING`)

**Imports from upstream modules:**
```python
from ..blueprint_validator.validation_report import (
    BlueprintValidationReport, STATUS_APPROVED, STATUS_REJECTED,
)
```

---

### 5.3 StructureReader

**File:** `structure_reader.py` (152 lines, 5,426 bytes)

**Class:** `StructureReader`

**Method:** `read(structure_map: ProjectStructureMap) -> Dict[str, Any]`

**Returns a dict with keys:**
- `files` — a list of `FileSummary`
- `relationships` — a list of `RelationshipSummary`
- `expansion_points` — a list of `ExpansionPoint`
- `build_order_map` — a dict mapping file path → build position
- `provenance_partial` — `{"structure_map_name": structure_map.project_name}`

**Internal methods:**

1. **`_read_files(structure_map)`** — Iterates `structure_map.files` (each a `FileEntry`), creating a `FileSummary` for each via `_file_entry_to_summary()`. Maps `fe.building_engine` → `responsible_engine`, `fe.build_order` → both `generation_priority` and `build_order`, `fe.purpose` → both `purpose` and `reason_for_existence`.

2. **`_read_relationships(structure_map)`** — Collects relationships from two sources:
   - Folder relationships: iterates `structure_map.folders`, then each folder's `.relationships`
   - File relationships: iterates `structure_map.files`, then each file's `.relationships`

3. **`_read_expansion_points(structure_map)`** — Iterates `structure_map.folders`, collecting those where `folder.scalable` is True.

4. **`_read_build_order_map(structure_map)`** — Iterates `structure_map.build_order` (each a `BuildOrderEntry`), building a dict of `entry.path` → `entry.position`.

**Imports from upstream modules:**
```python
from ..structure_generator.structure_map import (
    ProjectStructureMap, FileEntry, StructureRelationship, BuildOrderEntry,
)
```

---

### 5.4 RegistryReader

**File:** `registry_reader.py` (141 lines, 4,908 bytes)

**Class:** `RegistryReader`

**Method:** `read(registry: ComponentRegistry) -> Dict[str, Any]`

**Returns a dict with keys:**
- `components` — a list of `ComponentSummary`
- `relationships` — a list of `RelationshipSummary`
- `expansion_points` — a list of `ExpansionPoint`
- `build_order_map` — a dict mapping component name → build position
- `provenance_partial` — `{"component_registry_name": registry.project_name}`

**Internal methods:**

1. **`_read_components(registry)`** — Iterates `registry.components` (each a `DetectedComponent`), creating a `ComponentSummary` via `_component_to_summary()`. Maps `dc.depends_on` → `depends_on`, `dc.depended_by` → `depended_by`, leaves `files` and `dependencies` empty (filled by the assembler's cross-linking).

2. **`_read_relationships(registry)`** — Iterates `registry.relationships` (each a `ComponentDependencyEdge`), creating a `RelationshipSummary` for each.

3. **`_read_expansion_points(registry)`** — Iterates `registry.components`, collecting those where `dc.scalable` is True.

4. **`_read_build_order_map(registry)`** — Iterates `registry.build_order`, building a dict of `entry.component_name` → `entry.position`.

**Imports from upstream modules:**
```python
from ..component_detector.registry import (
    ComponentRegistry, DetectedComponent, ComponentDependencyEdge,
)
```

---

### 5.5 FilePlanReader

**File:** `file_plan_reader.py` (142 lines, 4,921 bytes)

**Class:** `FilePlanReader`

**Method:** `read(file_plan: FileGenerationPlan) -> Dict[str, Any]`

**Returns a dict with keys:**
- `files` — a list of `FileSummary`
- `relationships` — a list of `RelationshipSummary`
- `expansion_points` — a list of `ExpansionPoint`
- `build_order_map` — a dict mapping file path → build position
- `provenance_partial` — `{"file_plan_name": file_plan.project_name}`

**Internal methods:**

1. **`_read_files(file_plan)`** — Iterates `file_plan.files` (each a `FilePlanEntry`), creating a `FileSummary` via `_plan_entry_to_summary()`. Maps `fpe.reason_for_existence` → `reason_for_existence` (falls back to `fpe.purpose` if empty), `fpe.depends_on` → `depends_on`, `fpe.depended_by` → `depended_by`, `fpe.contains_code` → `contains_code`.

2. **`_read_relationships(file_plan)`** — Iterates `file_plan.relationships` (each a `FileRelationship`), creating a `RelationshipSummary` for each.

3. **`_read_expansion_points(file_plan)`** — Iterates `file_plan.files`, collecting those where `fpe.scalable` is True.

4. **`_read_build_order_map(file_plan)`** — Iterates `file_plan.generation_order`, building a dict of `entry.file_path` → `entry.position`.

**Imports from upstream modules:**
```python
from ..file_planner.plan_data import (
    FileGenerationPlan, FilePlanEntry, FileRelationship,
)
```

---

### 5.6 DependencyReader

**File:** `dependency_reader.py` (145 lines, 4,978 bytes)

**Class:** `DependencyReader`

**Method:** `read(report: DependencyResolutionReport) -> Dict[str, Any]`

**Returns a dict with keys:**
- `dependencies` — a list of `DependencySummary`
- `relationships` — a list of `RelationshipSummary`
- `findings` — a list of `ContextFinding`
- `load_order_map` — a dict mapping dependency name → load position
- `provenance_partial` — `{"dependency_report_name": report.project_name}`

**Internal methods:**

1. **`_read_dependencies(report)`** — Iterates `report.dependencies` (each a `DependencyEntry`), creating a `DependencySummary` via `_dependency_to_summary()`. Maps all fields directly: `dep.name`, `dep.type`, `dep.suggested_version`, `dep.version_constraint`, `dep.reason`, `dep.source_components`, `dep.priority`, `dep.load_order`, `dep.language`, `dep.framework`, `dep.depends_on`, `dep.depended_by`.

2. **`_read_relationships(report)`** — Iterates `report.relationships` (each a `DependencyRelationship`), creating a `RelationshipSummary` for each.

3. **`_read_findings(report)`** — Iterates `report.findings`, creating a `ContextFinding` for each (mapping all fields: `severity`, `code`, `message`, `affected`, `resolution_hint`, `category`).

4. **`_read_load_order_map(report)`** — Iterates `report.load_order`, building a dict of `entry.dependency_name` → `entry.position`.

**Imports from upstream modules:**
```python
from ..dependency_resolver.report_data import (
    DependencyResolutionReport, DependencyEntry, DependencyRelationship,
)
```

---

## 6. Context Assembler

**File:** `context_assembler.py` (443 lines, 16,341 bytes)

**Class:** `ContextAssembler`

The assembler is the "glue" that takes the partial data from each reader and assembles the complete, coherent context model. It is **stateless**.

### 6.1 Constructor

```python
def __init__(self) -> None:
    self._blueprint_reader = BlueprintReader()
    self._validation_reader = ValidationReader()
    self._structure_reader = StructureReader()
    self._registry_reader = RegistryReader()
    self._file_plan_reader = FilePlanReader()
    self._dependency_reader = DependencyReader()
```

### 6.2 Main Method

```python
def assemble(
    self,
    blueprint: Any,
    validation_report: Any,
    structure_map: Any,
    registry: Any,
    file_plan: Any,
    dependency_report: Any,
) -> ProjectContext:
```

**Steps performed:**

1. **Read each artefact** — calls each reader's `read()` method, obtaining six dicts of partial data.

2. **Assemble the context:**
   - `context.goal = bp_data["goal"]`
   - `context.features = bp_data["features"]`
   - `context.components = reg_data["components"]`
   - `context.files = self._merge_files(struct_files, plan_files, struct_order_map, plan_order_map)`
   - `context.dependencies = dep_data["dependencies"]`
   - `context.relationships = self._merge_relationships(bp, struct, reg, fp, dep relationship lists)`
   - `context.stages = self._enrich_stages(bp_stages, components, files, dependencies)`
   - `context.expansion_points = self._merge_expansion_points(bp, struct, reg, fp expansion point lists)`
   - `context.findings = self._merge_findings(val_findings, dep_findings)`
   - `context.provenance = self._build_provenance(bp, val, struct, reg, fp, dep data)`

3. **Cross-link:**
   - `_cross_link_features_and_components(features, components)`
   - `_cross_link_components_and_files(components, files)`
   - `_cross_link_components_and_dependencies(components, dependencies)`

### 6.3 File Merging (`_merge_files`)

The file plan is the **authoritative** source for file metadata. The structure map fills in any gaps.

**Algorithm:**
1. Add all files from the file plan first (they take precedence).
2. For each file in the structure map:
   - If not already in the merged dict, add it.
   - If already present, fill in missing fields (`reason_for_existence`, `source_component`) from the structure entry.
3. Update `build_order` from the order maps (plan order map takes precedence over structure order map).

### 6.4 Relationship Merging (`_merge_relationships`)

Accepts a variable number of relationship lists and deduplicates by the tuple `(source, target, kind)`. Uses a `seen` set of tuples to track duplicates.

### 6.5 Stage Enrichment (`_enrich_stages`)

Takes the base stages from the blueprint (which already have component names) and enriches them with files and dependencies.

**Algorithm:**
1. Build a `comp_to_files` map from the files' `source_component` fields.
2. Build a `comp_to_deps` map from the dependencies' `source_components` fields.
3. For each stage, collect files and dependencies from the components in that stage.
4. Deduplicate while preserving order using `dict.fromkeys()`.

### 6.6 Expansion-Point Merging (`_merge_expansion_points`)

Accepts a variable number of expansion point lists and deduplicates by `area`. Uses a `seen` set of area strings.

### 6.7 Finding Merging (`_merge_findings`)

Accepts a variable number of finding lists and simply concatenates them (no deduplication).

### 6.8 Provenance Building (`_build_provenance`)

Builds a `SourceProvenance` from all the provenance partial dicts. Uses:
- `blueprint_name` from `bp_data["goal"].name`
- `validation_status` from `val_partial`
- `structure_map_name` from `struct_partial`
- `component_registry_name` from `reg_partial`
- `file_plan_name` from `fp_partial`
- `dependency_report_name` from `dep_partial`
- `all_sources_used` = `list(ALL_SOURCES)`

### 6.9 Cross-Linking Methods

#### 6.9.1 `_cross_link_features_and_components`

**Algorithm:**
1. Build a `comp_map` (component name → `ComponentSummary`).
2. For each feature:
   - Start with the feature's existing `components` list (from the blueprint's `introduces_components`).
   - Also check all components for `source_feature == feature.name` and add them.
   - Sort the resulting list.
3. For each component in the feature's component list, if the component's `source_feature` is not set, update it to the feature's name.

#### 6.9.2 `_cross_link_components_and_files`

**Algorithm:**
1. Build a `comp_to_files` map from the files' `source_component` fields.
2. For each component, set `comp.files` to the list of file paths (deduplicated, order preserved).

#### 6.9.3 `_cross_link_components_and_dependencies`

**Algorithm:**
1. Build a `comp_to_deps` map from the dependencies' `source_components` fields.
2. For each component, set `comp.dependencies` to the list of dependency names (deduplicated, order preserved).

---

## 7. Context Linker

**File:** `context_linker.py` (302 lines, 11,071 bytes)

**Class:** `ContextLinker`

The linker builds the precomputed O(1) look-up indices and the context graph edges. It is **stateless**.

### 7.1 Main Method

```python
def link(self, context: ProjectContext) -> ProjectContext:
```

**Steps:**
1. Build the link list via `_build_links(context)`.
2. Build the indices via `_build_indices(context, links)`.
3. Set `context.links = links` and `context.indices = indices`.
4. Return the context (mutated in place).

### 7.2 Link List Building (`_build_links`)

Builds the complete list of `ContextLink` objects (edges in the context graph) from six sources:

1. **Feature → Component links:** For each feature, for each component name in `feature.components`, create a link with `kind=LINK_FEATURE_TO_COMPONENT`, `source_artefact=SOURCE_BLUEPRINT`.

2. **Component → File links:** For each component, for each file path in `comp.files`, create a link with `kind=LINK_COMPONENT_TO_FILE`, `source_artefact=SOURCE_COMPONENT_REGISTRY`.

3. **File → Dependency links (via component):** First builds a `comp_to_deps` map from `dependency.source_components`. Then for each component, for each file in the component, for each dependency the component requires, create a link with `kind=LINK_FILE_TO_DEPENDENCY`, `source_artefact=SOURCE_FILE_PLAN`.

4. **Component → Stage links:** Uses `_build_component_to_stage()` to build a `comp_to_stage` map. For each entry, create a link with `kind=LINK_COMPONENT_TO_STAGE`, `source_artefact=SOURCE_BLUEPRINT`.

5. **Dependency → Stage links:** Uses `_build_dependency_to_stage()` to build a `dep_to_stage` map. For each entry, create a link with `kind=LINK_DEPENDENCY_TO_STAGE`, `source_artefact=SOURCE_DEPENDENCY_REPORT`.

6. **Feature → Stage links (via component):** For each feature, find the first component's stage and create a link with `kind=LINK_FEATURE_TO_STAGE`, `source_artefact=SOURCE_BLUEPRINT`.

### 7.3 Index Building (`_build_indices`)

Builds 12 index maps on a `LinkIndices` object:

1. **`feature_to_components`** — For each feature, `feature.name` → `list(feature.components)`.

2. **`component_to_features`** — For each component, for each feature that includes the component, append the feature name to the component's entry.

3. **`component_to_files`** — For each component, `comp.name` → `list(comp.files)`.

4. **`file_to_components`** — For each file:
   - If `f.source_component`, add `f.path` to `file_to_components[f.source_component]`.
   - Also, for every component that lists this file in `comp.files`, add `f.path` to `file_to_components[comp.name]`.

5. **`file_to_dependencies`** — For each component, for each file in the component, set `file_to_dependencies[file_path]` to the component's dependencies (from the `comp_to_deps` map).

6. **`dependency_to_files`** — For each file's dependencies, add the file path to `dependency_to_files[dep_name]`.

7. **`dependency_to_components`** — For each dependency, `dep.name` → `list(dep.source_components)`.

8. **`component_to_dependencies`** — For each component, `comp.name` → `list(comp_to_deps.get(comp.name, []))`.

9. **`component_to_stage`** — From `_build_component_to_stage()`.

10. **`feature_to_stage`** — For each feature, find the first component's stage and map `feature.name` → stage name.

11. **`file_to_stage`** — For each file, if `f.source_component` is in `comp_to_stage`, map `f.path` → stage name.

12. **`dependency_to_stage`** — From `_build_dependency_to_stage()`.

### 7.4 Stage Mapping Helpers

#### 7.4.1 `_build_component_to_stage(context)`

Builds a `comp_to_stage` map by iterating all stages and their components:
```python
comp_to_stage = {}
for stage in context.stages:
    for comp_name in stage.components:
        comp_to_stage[comp_name] = stage.name
return comp_to_stage
```

#### 7.4.2 `_build_dependency_to_stage(context, comp_to_stage)`

Builds a `dep_to_stage` map. A dependency belongs to the same stage as the components that require it. When a dependency is required by components in multiple stages, it is assigned to the **earliest** (lowest phase) stage.

**Algorithm:**
1. Build a `stage_phase` map (stage name → phase number).
2. For each dependency:
   - Iterate its `source_components`.
   - For each component, look up its stage via `comp_to_stage`.
   - Track the stage with the lowest phase number.
   - If found, map `dep.name` → best stage name.

---

## 8. Context Validator

**File:** `context_validator.py` (360 lines, 13,791 bytes)

**Class:** `ContextValidator`

The validator checks the unified `ProjectContext` for internal consistency. It is **stateless**.

### 8.1 Main Method

```python
def validate(self, context: ProjectContext) -> List[ContextFinding]:
```

Calls seven check methods and concatenates their findings:

1. `_check_duplicate_names(context)`
2. `_check_features_without_components(context)`
3. `_check_components_without_files(context)`
4. `_check_files_without_responsibility(context)`
5. `_check_unknown_elements_in_relationships(context)`
6. `_check_stages_without_components(context)`
7. `_check_orphaned_components(context)`

### 8.2 Check Methods

#### 8.2.1 `_check_duplicate_names`

Checks for duplicate names across four entity types:

| Check | Severity | Code | Message |
|-------|----------|------|---------|
| Duplicate feature names | `SEVERITY_ERROR` | `duplicate_feature_name` | "Duplicate feature name '{name}'. Feature names must be unique." |
| Duplicate component names | `SEVERITY_ERROR` | `duplicate_component_name` | "Duplicate component name '{name}'. Component names must be unique." |
| Duplicate file paths | `SEVERITY_ERROR` | `duplicate_file_path` | "Duplicate file path '{path}'. File paths must be unique." |
| Duplicate dependency names | `SEVERITY_ERROR` | `duplicate_dependency_name` | "Duplicate dependency name '{name}'. Dependency names must be unique." |

All findings have `category="consistency"` and include a `resolution_hint`.

#### 8.2.2 `_check_features_without_components`

For each feature with an empty `components` list, produces a `SEVERITY_WARNING` finding with `code="feature_without_components"`, `category="linking"`, and resolution hint "Ensure the component detector detects components for this feature."

#### 8.2.3 `_check_components_without_files`

For each component with an empty `files` list, produces a `SEVERITY_WARNING` finding with `code="component_without_files"`, `category="linking"`, and resolution hint "Ensure the file planner plans files for this component."

#### 8.2.4 `_check_files_without_responsibility`

For each file with no `source_component` and no `responsible_engine`, produces a `SEVERITY_WARNING` finding with `code="file_without_responsibility"`, `category="linking"`, and resolution hint "Assign this file to a component or specify a responsible engine."

#### 8.2.5 `_check_unknown_elements_in_relationships`

Builds a set of all known element names (components, files, dependencies, features). For each relationship, checks that both `source` and `target` are in the known set. Unknown sources produce `code="unknown_relationship_source"` and unknown targets produce `code="unknown_relationship_target"`. Both are `SEVERITY_WARNING` with `category="consistency"`.

#### 8.2.6 `_check_stages_without_components`

For each stage with no components, no files, and no dependencies, produces a `SEVERITY_INFO` finding with `code="empty_stage"`, `category="consistency"`, and resolution hint "This stage may be skippable or may require components to be assigned."

#### 8.2.7 `_check_orphaned_components`

Builds a set of all component names that appear in any stage. For each component not in any stage (only when `context.stages` is non-empty), produces a `SEVERITY_INFO` finding with `code="orphaned_component"`, `category="consistency"`, and resolution hint "Assign this component to the appropriate stage in the execution plan."

---

## 9. Project Context Engine

**File:** `project_context_engine.py` (414 lines, 16,728 bytes)

**Class:** `ProjectContextEngine(BaseEngine)`

This is the main engine class that orchestrates all the steps.

### 9.1 Constructor

```python
def __init__(self) -> None:
    super().__init__(
        name="project_context",
        version="1.0.0",
        description="Builds the complete, unified project context...",
        tags=["generation", "context", "merging"],
        metadata={"phase": "build_context"},
    )
    self._assembler = ContextAssembler()
    self._linker = ContextLinker()
    self._validator = ContextValidator()
```

### 9.2 Execute Method

```python
def execute(self, context: GenerationContext) -> StageResult:
```

**Seven steps:**

#### Step 1: Obtain the six artefacts

Obtains each artefact from the context via `context.get(key)`. If any is `None`, returns `self.failed()` with a descriptive error message:

| Missing Artefact | Error Message |
|-----------------|---------------|
| `project_blueprint` | "No 'project_blueprint' artefact found. The Project Context Engine requires the Project Planning Engine to have run first." |
| `blueprint_validation_report` | "No 'blueprint_validation_report' artefact found. The Project Context Engine requires the Blueprint Validator Engine to have run first." |
| `project_structure_map` | "No 'project_structure_map' artefact found. The Project Context Engine requires the Structure Generation Engine to have run first." |
| `component_registry` | "No 'component_registry' artefact found. The Project Context Engine requires the Component Detection Engine to have run first." |
| `file_generation_plan` | "No 'file_generation_plan' artefact found. The Project Context Engine requires the File Generation Planning Engine to have run first." |
| `dependency_resolution_report` | "No 'dependency_resolution_report' artefact found. The Project Context Engine requires the Dependency Resolution Engine to have run first." |

#### Step 2: Type-check the artefacts

Uses `isinstance()` to verify each artefact is the correct type. If any fails, returns `self.failed()` with a descriptive error message:

| Artefact | Expected Type |
|----------|---------------|
| `project_blueprint` | `ProjectBlueprint` |
| `blueprint_validation_report` | `BlueprintValidationReport` |
| `project_structure_map` | `ProjectStructureMap` |
| `component_registry` | `ComponentRegistry` |
| `file_generation_plan` | `FileGenerationPlan` |
| `dependency_resolution_report` | `DependencyResolutionReport` |

After type-checking, logs an INFO message with the blueprint name, feature count, component count, structure file count, file plan file count, dependency count, and validation status.

#### Step 3: Assemble the context

Calls `self._assembler.assemble(blueprint, validation_report, structure_map, registry, file_plan, dependency_report)` and logs the assembled counts (features, components, files, dependencies, stages, relationships).

#### Step 4: Build the context graph

Calls `self._linker.link(project_context)` and logs the link count, feature-to-components count, component-to-files count, and file-to-dependencies count.

#### Step 5: Validate the context

Calls `self._validator.validate(project_context)` and extends `project_context.findings` with the validation findings. Logs the validation finding count, error count, and warning count.

#### Step 6: Build the summary and notes

- Calls `_build_summary(project_context, total_duration_ms)` to build a human-readable summary string.
- Calls `_build_notes(project_context, validation_report)` to build the notes list.
- Collects warning messages from findings where `severity == SEVERITY_WARNING` into `project_context.warnings`.

#### Step 7: Store the context

- `context.set("project_context", project_context)`
- `context.metadata["project_context"] = project_context`

Separates error and warning findings. If there are error findings, returns `self.failed()` with formatted error messages `"[{code}] {message}"`, the project context as output, and the warning messages. Otherwise, returns `self.ok()` with the project context as output and a metadata dict with all counts and the duration.

### 9.3 Helper Methods

#### `_build_summary(context, duration_ms)`

Returns a string:
```
"Built project context with {N} feature(s), {N} component(s), {N} file(s), {N} dependency(ies), {N} stage(s), {N} relationship(s), and {N} context link(s). {N} error(s), {N} warning(s). Generated in {ms} ms."
```

#### `_build_notes(context, validation_report)`

Returns a list of 8 strings:
1. "Project context generated at {ISO timestamp}."
2. "Source blueprint: {blueprint_name or 'unnamed'}."
3. "Validation status: {validation_status or 'unknown'}."
4. "Source structure map: {structure_map_name or 'unnamed'}."
5. "Source component registry: {component_registry_name or 'unnamed'}."
6. "Source file generation plan: {file_plan_name or 'unnamed'}."
7. "Source dependency resolution report: {dependency_report_name or 'unnamed'}."
8. "All sources used: {comma-separated all_sources_used}."

### 9.4 Result Metadata

On success, `self.ok()` returns metadata with:
- `project_name`
- `feature_count`
- `component_count`
- `file_count`
- `dependency_count`
- `stage_count`
- `link_count`
- `relationship_count`
- `error_count`
- `warning_count`
- `duration_ms` (rounded to 2 decimal places)

---

## 10. Package Exports (__init__.py)

**File:** `__init__.py` (131 lines, 3,959 bytes)

The `__init__.py` re-exports all public classes and constants:

**Engine:**
- `ProjectContextEngine`

**Data Model:**
- `ProjectContext`
- `ProjectGoal`
- `FeatureSummary`
- `ComponentSummary`
- `FileSummary`
- `DependencySummary`
- `RelationshipSummary`
- `ExecutionStage`
- `ContextLink`
- `ExpansionPoint`
- `ContextFinding`
- `LinkIndices`
- `SourceProvenance`

**Source-Artefact Constants:**
- `SOURCE_BLUEPRINT`
- `SOURCE_VALIDATION`
- `SOURCE_STRUCTURE`
- `SOURCE_COMPONENT_REGISTRY`
- `SOURCE_FILE_PLAN`
- `SOURCE_DEPENDENCY_REPORT`
- `ALL_SOURCES`

**Severity Constants:**
- `SEVERITY_ERROR`
- `SEVERITY_WARNING`
- `SEVERITY_INFO`
- `ALL_SEVERITIES`

**Link-Kind Constants:**
- `LINK_FEATURE_TO_COMPONENT`
- `LINK_COMPONENT_TO_FILE`
- `LINK_FILE_TO_DEPENDENCY`
- `LINK_DEPENDENCY_TO_STAGE`
- `LINK_COMPONENT_TO_STAGE`
- `LINK_FEATURE_TO_STAGE`
- `ALL_LINK_KINDS`

**Helpers:**
- `ContextAssembler`
- `ContextLinker`
- `ContextValidator`
- `BlueprintReader`
- `ValidationReader`
- `StructureReader`
- `RegistryReader`
- `FilePlanReader`
- `DependencyReader`

---

## 11. Integration

### 11.1 Generators Package

**File:** `telegram_bot_engine/engines/generators/__init__.py`

The engine is imported and exported:
```python
from .project_context import ProjectContextEngine
```
And added to `__all__`:
```python
"ProjectContextEngine",
```

### 11.2 Bootstrap Registration

**File:** `telegram_bot_engine/core/bootstrap.py`

The engine is instantiated and registered in two places:

1. **EngineRegistry:**
   ```python
   project_context_engine = ProjectContextEngine()
   registry.register_engine(project_context_engine)
   ```

2. **CoreEngineManager:**
   ```python
   manager.register(project_context_engine, engine_id="project_context",
                    priority=96, dependencies=["dependency_resolver"])
   ```

**Priority:** 96 (after dependency_resolver at 95)
**Dependencies:** `["dependency_resolver"]`

---

## 12. Test Suite

**File:** `tests/test_project_context.py` (2,870 lines, 102,204 bytes)

### 12.1 Test Results

```
Results: 125 passed, 0 failed, 125 total
```

### 12.2 Test Categories

The 125 test functions are organized into 18 categories:

#### Data Model Tests (27 tests)

| Test | Description |
|------|-------------|
| `test_project_goal_creation` | ProjectGoal construction with default values |
| `test_project_goal_to_dict` | ProjectGoal serialisation |
| `test_feature_summary_creation` | FeatureSummary construction |
| `test_feature_summary_to_dict` | FeatureSummary serialisation |
| `test_component_summary_creation` | ComponentSummary construction |
| `test_component_summary_to_dict` | ComponentSummary serialisation |
| `test_file_summary_creation` | FileSummary construction |
| `test_file_summary_to_dict` | FileSummary serialisation |
| `test_dependency_summary_creation` | DependencySummary construction |
| `test_dependency_summary_to_dict` | DependencySummary serialisation |
| `test_relationship_summary_creation` | RelationshipSummary construction |
| `test_relationship_summary_to_dict` | RelationshipSummary serialisation |
| `test_execution_stage_creation` | ExecutionStage construction |
| `test_execution_stage_to_dict` | ExecutionStage serialisation |
| `test_context_link_creation` | ContextLink construction |
| `test_context_link_to_dict` | ContextLink serialisation |
| `test_expansion_point_creation` | ExpansionPoint construction |
| `test_expansion_point_to_dict` | ExpansionPoint serialisation |
| `test_context_finding_creation` | ContextFinding construction |
| `test_context_finding_to_dict` | ContextFinding serialisation |
| `test_link_indices_creation` | LinkIndices construction |
| `test_link_indices_to_dict` | LinkIndices serialisation |
| `test_source_provenance_creation` | SourceProvenance construction |
| `test_source_provenance_to_dict` | SourceProvenance serialisation |
| `test_source_artefact_constants` | All 6 source-artefact constants |
| `test_severity_constants` | All 3 severity constants |
| `test_link_kind_constants` | All 6 link-kind constants |

#### ProjectContext Convenience Properties (4 tests)

| Test | Description |
|------|-------------|
| `test_project_context_empty` | `is_empty` property |
| `test_project_context_counts` | All count properties |
| `test_project_context_add_finding` | `add_finding` method |
| `test_project_context_get_methods` | All `get_*` methods |

#### BlueprintReader Tests (5 tests)

| Test | Description |
|------|-------------|
| `test_blueprint_reader_goal` | Goal extraction |
| `test_blueprint_reader_features` | Feature extraction |
| `test_blueprint_reader_relationships` | Relationship extraction |
| `test_blueprint_reader_stages` | Stage extraction from ExecutionPlan |
| `test_blueprint_reader_expansion_points` | Expansion point extraction |

#### ValidationReader Tests (2 tests)

| Test | Description |
|------|-------------|
| `test_validation_reader_status` | Validation status and quality scores |
| `test_validation_reader_findings` | Finding extraction from layers, conflicts, errors, warnings, missing info |

#### StructureReader Tests (3 tests)

| Test | Description |
|------|-------------|
| `test_structure_reader_files` | File extraction from structure map |
| `test_structure_reader_provenance` | Provenance partial dict |
| `test_structure_reader_build_order_map` | Build order map extraction |

#### RegistryReader Tests (3 tests)

| Test | Description |
|------|-------------|
| `test_registry_reader_components` | Component extraction |
| `test_registry_reader_provenance` | Provenance partial dict |
| `test_registry_reader_expansion_points` | Expansion point extraction |

#### FilePlanReader Tests (3 tests)

| Test | Description |
|------|-------------|
| `test_file_plan_reader_files` | File extraction from file plan |
| `test_file_plan_reader_relationships` | Relationship extraction |
| `test_file_plan_reader_provenance` | Provenance partial dict |

#### DependencyReader Tests (4 tests)

| Test | Description |
|------|-------------|
| `test_dependency_reader_dependencies` | Dependency extraction |
| `test_dependency_reader_relationships` | Relationship extraction |
| `test_dependency_reader_findings` | Finding extraction |
| `test_dependency_reader_provenance` | Provenance partial dict |

#### ContextAssembler Tests (8 tests)

| Test | Description |
|------|-------------|
| `test_assembler_produces_project_context` | Produces a valid ProjectContext |
| `test_assembler_goal` | Goal is set correctly |
| `test_assembler_features_have_components` | Features are cross-linked with components |
| `test_assembler_components_have_files` | Components are cross-linked with files |
| `test_assembler_components_have_dependencies` | Components are cross-linked with dependencies |
| `test_assembler_deduplicates_relationships` | Relationships are deduplicated by (source, target, kind) |
| `test_assembler_provenance` | Provenance records all sources |
| `test_assembler_stages_enriched` | Stages are enriched with files and dependencies |

#### ContextLinker Tests (13 tests)

| Test | Description |
|------|-------------|
| `test_linker_builds_links` | Links list is non-empty |
| `test_linker_feature_to_component_links` | Feature → Component links |
| `test_linker_component_to_file_links` | Component → File links |
| `test_linker_file_to_dependency_links` | File → Dependency links |
| `test_linker_component_to_stage_links` | Component → Stage links |
| `test_linker_dependency_to_stage_links` | Dependency → Stage links |
| `test_linker_indices_feature_to_components` | feature_to_components index |
| `test_linker_indices_component_to_files` | component_to_files index |
| `test_linker_indices_file_to_dependencies` | file_to_dependencies index |
| `test_linker_indices_dependency_to_components` | dependency_to_components index |
| `test_linker_indices_component_to_stage` | component_to_stage index |
| `test_linker_indices_dependency_to_stage` | dependency_to_stage index |
| `test_linker_o1_lookup_methods` | O(1) look-up methods on ProjectContext |

#### ContextValidator Tests (7 tests)

| Test | Description |
|------|-------------|
| `test_validator_no_findings_on_valid_context` | No findings on a well-formed context |
| `test_validator_duplicate_feature_names` | Detects duplicate feature names |
| `test_validator_duplicate_component_names` | Detects duplicate component names |
| `test_validator_feature_without_components` | Detects features without components |
| `test_validator_component_without_files` | Detects components without files |
| `test_validator_file_without_responsibility` | Detects files without responsibility |
| `test_validator_unknown_elements_in_relationships` | Detects unknown elements |

#### Engine Data Source Tests (7 tests)

| Test | Description |
|------|-------------|
| `test_engine_requires_blueprint` | Fails when project_blueprint is missing |
| `test_engine_requires_validation_report` | Fails when blueprint_validation_report is missing |
| `test_engine_requires_structure_map` | Fails when project_structure_map is missing |
| `test_engine_requires_component_registry` | Fails when component_registry is missing |
| `test_engine_requires_file_plan` | Fails when file_generation_plan is missing |
| `test_engine_requires_dependency_report` | Fails when dependency_resolution_report is missing |
| `test_engine_does_not_read_request` | Engine does not read the raw request |

#### Engine Type-Checking Tests (6 tests)

| Test | Description |
|------|-------------|
| `test_engine_type_check_blueprint` | Fails when blueprint is wrong type |
| `test_engine_type_check_validation_report` | Fails when validation report is wrong type |
| `test_engine_type_check_structure_map` | Fails when structure map is wrong type |
| `test_engine_type_check_registry` | Fails when registry is wrong type |
| `test_engine_type_check_file_plan` | Fails when file plan is wrong type |
| `test_engine_type_check_dependency_report` | Fails when dependency report is wrong type |

#### Engine Output Tests (9 tests)

| Test | Description |
|------|-------------|
| `test_engine_produces_project_context` | Produces a ProjectContext in outputs |
| `test_engine_context_stored_in_metadata` | Context stored in context.metadata |
| `test_engine_records_provenance` | Provenance records all sources |
| `test_engine_context_has_summary` | Context has a summary string |
| `test_engine_context_has_notes` | Context has notes list |
| `test_engine_context_has_stages` | Context has non-empty stages |
| `test_engine_context_has_links` | Context has non-empty links |
| `test_engine_metadata_in_result` | Result metadata has all counts |
| `test_engine_context_no_errors` | Context has no error-level findings |

#### Context Integrity Tests (6 tests)

| Test | Description |
|------|-------------|
| `test_context_all_features_have_components` | All features have components |
| `test_context_all_components_have_files` | All components have files |
| `test_context_no_duplicate_components` | No duplicate component names |
| `test_context_no_duplicate_files` | No duplicate file paths |
| `test_context_no_duplicate_dependencies` | No duplicate dependency names |
| `test_context_provenance_all_sources` | Provenance lists all 6 sources |

#### Bootstrap Tests (3 tests)

| Test | Description |
|------|-------------|
| `test_bootstrap_registers_project_context` | Engine is registered in the registry |
| `test_bootstrap_project_context_priority` | Engine has priority 96 |
| `test_bootstrap_project_context_dependencies` | Engine depends on dependency_resolver |

#### Serialisation Tests (13 tests)

| Test | Description |
|------|-------------|
| `test_project_goal_serialisation` | Round-trip serialisation |
| `test_feature_summary_serialisation` | Round-trip serialisation |
| `test_component_summary_serialisation` | Round-trip serialisation |
| `test_file_summary_serialisation` | Round-trip serialisation |
| `test_dependency_summary_serialisation` | Round-trip serialisation |
| `test_relationship_summary_serialisation` | Round-trip serialisation |
| `test_execution_stage_serialisation` | Round-trip serialisation |
| `test_context_link_serialisation` | Round-trip serialisation |
| `test_expansion_point_serialisation` | Round-trip serialisation |
| `test_context_finding_serialisation` | Round-trip serialisation |
| `test_link_indices_serialisation` | Round-trip serialisation |
| `test_source_provenance_serialisation` | Round-trip serialisation |
| `test_project_context_to_dict` | Full ProjectContext serialisation |

#### End-to-End Tests (2 tests)

| Test | Description |
|------|-------------|
| `test_end_to_end_full_pipeline` | Full pipeline: 6 artefacts → ProjectContext |
| `test_end_to_end_with_dependency_resolver` | Full pipeline including the real Dependency Resolution Engine |

### 12.3 Test Fixtures

The test file uses aliased imports for the project_context constants (prefixed with `PC_`) to avoid conflicts with the dependency_resolver constants (prefixed with `DR_`).

**Key fixture functions:**

| Function | Description |
|----------|-------------|
| `make_config()` | Returns `build_configuration()` |
| `make_context(blueprint, validation_report, structure_map, registry, file_plan, dependency_report)` | Builds a `GenerationContext` with all 6 artefacts set |
| `make_valid_blueprint(name)` | Builds a `ProjectBlueprint` with 3 components, 1 feature, and an `ExecutionPlan` with 3 phases |
| `make_approved_report(name)` | Returns a `BlueprintValidationReport` with `STATUS_APPROVED` |
| `make_structure_map(name)` | Builds a `ProjectStructureMap` with 4 folders, 7 files |
| `make_component_registry(name)` | Builds a `ComponentRegistry` with 3 components |
| `make_file_plan(name)` | Builds a `FileGenerationPlan` with 4 entries |
| `make_dependency_report(name)` | Builds a `DependencyResolutionReport` with 4 dependencies |
| `make_full_context(name)` | Calls all 6 fixtures and builds a full `GenerationContext` |
| `_make_assembled_context()` | Assembles and links a context for linker/validator tests |

---

## 13. Constants Reference

### 13.1 Source-Artefact Constants

```python
SOURCE_BLUEPRINT = "blueprint"
SOURCE_VALIDATION = "validation"
SOURCE_STRUCTURE = "structure"
SOURCE_COMPONENT_REGISTRY = "component_registry"
SOURCE_FILE_PLAN = "file_plan"
SOURCE_DEPENDENCY_REPORT = "dependency_report"

ALL_SOURCES = (
    SOURCE_BLUEPRINT,
    SOURCE_VALIDATION,
    SOURCE_STRUCTURE,
    SOURCE_COMPONENT_REGISTRY,
    SOURCE_FILE_PLAN,
    SOURCE_DEPENDENCY_REPORT,
)
```

### 13.2 Severity Constants

```python
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

ALL_SEVERITIES = (SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO)
```

### 13.3 Link-Kind Constants

```python
LINK_FEATURE_TO_COMPONENT = "feature_to_component"
LINK_COMPONENT_TO_FILE = "component_to_file"
LINK_FILE_TO_DEPENDENCY = "file_to_dependency"
LINK_DEPENDENCY_TO_STAGE = "dependency_to_stage"
LINK_COMPONENT_TO_STAGE = "component_to_stage"
LINK_FEATURE_TO_STAGE = "feature_to_stage"

ALL_LINK_KINDS = (
    LINK_FEATURE_TO_COMPONENT,
    LINK_COMPONENT_TO_FILE,
    LINK_FILE_TO_DEPENDENCY,
    LINK_DEPENDENCY_TO_STAGE,
    LINK_COMPONENT_TO_STAGE,
    LINK_FEATURE_TO_STAGE,
)
```

---

## 14. Data Flow Diagram

```
                    ┌─────────────────────────────────────────────────┐
                    │           GenerationContext                     │
                    │                                                 │
                    │  ┌─────────────────────────────────────────┐   │
                    │  │ project_blueprint                        │   │
                    │  │ blueprint_validation_report              │   │
                    │  │ project_structure_map                    │   │
                    │  │ component_registry                       │   │
                    │  │ file_generation_plan                     │   │
                    │  │ dependency_resolution_report             │   │
                    │  └──────────────┬──────────────────────────┘   │
                    └─────────────────┼──────────────────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │      ProjectContextEngine        │
                    │       .execute(context)          │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │      ContextAssembler            │
                    │       .assemble(...)             │
                    └────────────────┬────────────────┘
                                     │
            ┌──────────────┬────────┼────────┬──────────────┐
            │              │        │        │              │
     ┌──────▼─────┐ ┌─────▼────┐ ┌─▼──────┐ ┌▼──────────┐ ┌─▼──────────────┐
     │BlueprintRdr│ │ValRdr    │ │StructRdr│ │RegistryRdr│ │FilePlanRdr    │
     │            │ │          │ │         │ │           │ │               │
     │ goal       │ │ status   │ │ files   │ │ components│ │ files         │
     │ features   │ │ quality  │ │ rels    │ │ rels      │ │ rels          │
     │ rels       │ │ findings │ │ exp.pts │ │ exp.pts   │ │ exp.pts       │
     │ stages     │ │          │ │ bld.ord │ │ bld.ord   │ │ bld.ord       │
     │ exp.pts    │ │          │ │         │ │           │ │               │
     └──────┬─────┘ └─────┬────┘ └────┬────┘ └─────┬─────┘ └─────┬─────────┘
            │              │           │             │             │
            └──────────────┴───────────┼─────────────┴─────────────┘
                                        │
                               ┌────────▼────────┐
                               │ DependencyReader│
                               │  dependencies   │
                               │  relationships  │
                               │  findings       │
                               │  load_order_map │
                               └────────┬────────┘
                                        │
                    ┌───────────────────▼────────────────────┐
                    │         Merged ProjectContext          │
                    │                                       │
                    │  goal, features, components, files,   │
                    │  dependencies, relationships, stages, │
                    │  expansion_points, findings,          │
                    │  provenance                            │
                    │                                       │
                    │  Cross-linked: features↔components,    │
                    │  components↔files,                    │
                    │  components↔dependencies              │
                    └───────────────────┬────────────────────┘
                                        │
                    ┌───────────────────▼────────────────────┐
                    │           ContextLinker                │
                    │            .link(context)              │
                    │                                       │
                    │  Builds: links[], indices{}           │
                    │  12 O(1) index maps                   │
                    │  6 link kinds                         │
                    └───────────────────┬────────────────────┘
                                        │
                    ┌───────────────────▼────────────────────┐
                    │          ContextValidator              │
                    │           .validate(context)           │
                    │                                       │
                    │  7 check methods:                     │
                    │  - duplicate names                    │
                    │  - features without components        │
                    │  - components without files           │
                    │  - files without responsibility       │
                    │  - unknown elements in relationships  │
                    │  - empty stages                       │
                    │  - orphaned components                │
                    └───────────────────┬────────────────────┘
                                        │
                    ┌───────────────────▼────────────────────┐
                    │         Final ProjectContext           │
                    │                                       │
                    │  Stored as: context.set("project_     │
                    │  context", project_context)           │
                    │  Also: context.metadata[              │
                    │  "project_context"] = project_context │
                    │                                       │
                    │  Returns: self.ok(outputs={           │
                    │    "project_context": project_context},│
                    │    metadata={...})                    │
                    └────────────────────────────────────────┘
```

---

## 15. Design Principles

### 15.1 One Unified Model

Every downstream engine reads the `ProjectContext` instead of re-reading the individual upstream artefacts. This eliminates redundant parsing and keeps the understanding of the project in a single place.

### 15.2 Traceability

Every piece of information inside the Project Context records the artefact it came from (`source_artefact`). Any decision taken by a downstream engine can trace its data back to the original source.

### 15.3 Context Linking

Features are linked to the components that implement them, components are linked to the files that contain them, files are linked to the dependencies they require, and everything is linked to the execution stage it belongs to. A downstream engine can start from any point (a feature, a component, a file, a dependency) and reach any other point in O(1) time using the link indices.

### 15.4 No Build Decisions

The Project Context provides **information**, not decisions. It does not decide which file to generate first, which library to install first, or how to structure the code. It only provides the data so that decision-making engines can act.

### 15.5 Validation

The context is validated for internal consistency: no conflicting data, no unknown elements, no features without components, no components without files, no files without responsibility.

### 15.6 Performance

The context is built once and queried many times. Look-up indices (by name, by type, by source) are precomputed so that downstream engines can access any information in constant time without re-analysing the project.

### 15.7 Scalability

The context is a plain data container that grows linearly with the number of features, components, files, and dependencies. No O(n²) operations are performed during construction or querying. The context works equally well for small, medium, and very large projects.

### 15.8 Read-Only for Downstream

The Project Context is **read-only** for all downstream engines — no engine may modify it directly. Any modification requires a dedicated engine.

### 15.9 Forbidden from Reading the Request

The engine is **forbidden** from reading the user's request. It reads only the six upstream artefacts.

---

## Document Information

- **Specification:** 010 — Project Context Engine
- **Status:** COMPLETE
- **Source Files:** 12 files, 3,663 lines, 131,460 bytes
- **Test Suite:** 125 tests, all passing (0 failures)
- **Test File:** 2,870 lines, 102,204 bytes
- **Priority in Pipeline:** 96
- **Dependencies:** `["dependency_resolver"]`
- **Engine Name:** `project_context`
- **Engine Version:** `1.0.0`
- **Engine Tags:** `["generation", "context", "merging"]`
- **Engine Phase:** `build_context`

---

*This documentation was generated from the actual source code. Every detail has been verified against the implementation.*
