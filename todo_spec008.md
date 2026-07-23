# Specification 008 — File Generation Planning Engine

## Implementation Plan

### Phase 1: Data Model
- [x] Create `telegram_bot_engine/engines/generators/file_planner/plan_data.py`

### Phase 2: Helper Classes
- [x] Create `component_analyzer.py` — ComponentAnalyzer (analyzes all components from the registry to determine required files per component)
- [x] Create `file_determiner.py` — FileDeterminer (determines required files per component, assigns metadata)
- [x] Create `relationship_resolver.py` — RelationshipResolver (determines file relationships/dependencies)
- [x] Create `generation_order_computer.py` — GenerationOrderComputer (topological sort for creation order)
- [x] Create `conflict_detector.py` — ConflictDetector (duplicate files, naming conflicts, useless files, unlinked files)
- [x] Create `plan_validator.py` — PlanValidator (validates plan: all components have files, all files have purpose, all relationships valid, generation order valid)

### Phase 3: Main Engine
- [x] Create `file_planning_engine.py` — FileGenerationPlanningEngine(BaseEngine)
  - Reads 4 artefacts: project_blueprint, blueprint_validation_report, project_structure_map, component_registry
  - Does NOT read user's request
  - Produces `file_generation_plan` artefact
  - Orchestrates all helpers

### Phase 4: Package Init
- [x] Create `__init__.py` re-exporting all public classes and constants

### Phase 5: Integration
- [x] Register engine in `generators/__init__.py`
- [x] Register engine in `core/bootstrap.py`
- [x] Add config section in `configuration/defaults.py`

### Phase 6: Tests
- [x] Create `tests/test_file_planner.py` with comprehensive tests (78 tests)

### Phase 7: Verification
- [x] Run tests and verify all pass (78/78 passed)
- [x] Verify engine does not read user request (test_engine_does_not_read_request — PASS)
- [x] Verify all existing tests still pass (blueprint_validator: ✅, project_planner: 288 ✅, structure_generator: 61 ✅)
