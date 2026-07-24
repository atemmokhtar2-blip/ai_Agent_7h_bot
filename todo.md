# Telegram Bot Generation Engine — Master Plan

## Phase 1: Core Architecture (Specification 001) ✅ COMPLETE
- [x] Full architecture (44 files, 14 modules)

## Phase 2: Core Request Analyzer Engine (Specification 002) ✅ COMPLETE
- [x] All 10 stages implemented and tested
- [x] Register analyzer in bootstrap
- [x] 6 test cases, all pass

## Phase 3: Core Engine Manager (Specification 003) ✅ COMPLETE
- [x] All manager components (errors, lifecycle, engine_entry, execution_queue, engine_manager)
- [x] Wired into bootstrap (3-tuple return)
- [x] 53 tests pass
- [x] STOP and wait for Specification 004 ✅

## Phase 4: Project Planning Engine (Specification 004) ✅ COMPLETE
### Data Model
- [x] project_planner/blueprint.py — ProjectBlueprint and all sub-dataclasses
- [x] project_planner/feature_unit.py — FeatureUnit + priority constants
- [x] project_planner/dependency_graph.py — DependencyGraph with topological sort
- [x] project_planner/execution_plan.py — 8-phase ExecutionPlan
- [x] project_planner/risk_detection.py — RiskDetector
- [x] project_planner/validation.py — BlueprintValidator
### Engine
- [x] project_planner/planning_engine.py — ProjectPlanningEngine
- [x] project_planner/__init__.py — exports
### Integration
- [x] Wire ProjectPlanningEngine into generators __init__.py
- [x] Wire ProjectPlanningEngine into bootstrap (registry + manager)
### Bug Fixes
- [x] Fix import paths (4-dot relative imports for deeper package)
- [x] Fix phase name mismatches (phase_N_xxx → bare names matching DEFAULT_PHASES)
- [x] Fix self-loop in dependency graph (feature→component with same name)
- [x] Fix empty phases 6, 7, 8 (add default tasks)
- [x] Verify functional end-to-end test passes
### Testing
- [x] Create comprehensive test script (tests/test_project_planner.py) — 288 tests across 14 groups
- [x] Run tests and verify all pass — 288/288 passed
- [x] Fix test bugs: orphan feature test needed 2+ features; end-to-end test needed full lifecycle + polling keyword
### Completion
- [x] STOP and wait for Specification 005
## Phase 9: PDFX AI Visual Page Reconstruction Engine (Specification 009) ✅ COMPLETE
### Data Model
- [x] visual_page_reconstruction/page_analysis.py — PageAnalysis, PageElement, ElementPosition, VisualLayer, PageImage, PageText, PageChoice, PageTable, PageEquation, PageSeparator, PageDimensions
### Helpers
- [x] visual_page_reconstruction/image_extractor.py — ImageExtractor
- [x] visual_page_reconstruction/page_analyzer.py — PageAnalyzer
- [x] visual_page_reconstruction/layout_rebuilder.py — LayoutRebuilder
- [x] visual_page_reconstruction/choice_detector.py — ChoiceDetector
- [x] visual_page_reconstruction/coordinate_mapper.py — CoordinateMapper
- [x] visual_page_reconstruction/visual_validator.py — VisualValidator, VisualSimilarityReport
### Engine
- [x] visual_page_reconstruction/page_reconstruction_engine.py — VisualPageReconstructionEngine
- [x] visual_page_reconstruction/__init__.py — exports
### Integration
- [x] Wire VisualPageReconstructionEngine into generators __init__.py
- [x] Wire VisualPageReconstructionEngine into bootstrap (registry + manager, priority 90)
- [x] Create visual_reconstruction_stage.py pipeline stage
- [x] Wire stage into pipeline/stages __init__.py
### Testing
- [x] Create comprehensive test script (tests/test_visual_page_reconstruction.py) — 119 tests across 14 groups
- [x] Run tests and verify all pass — 119/119 passed
- [x] Fix manager._entries vs _engines in tests
- [x] Fix GenerationContext signature in tests
- [x] Fix reportlab import (remove point)
- [x] Fix existing tests (manager: 6→9 engines, project_planner: 8→9 engines)
### Acceptance
- [x] All elements have X, Y, Width, Height, Rotation, Layer
- [x] No element omitted or merged
- [x] Images from embedded PDF streams (not screenshots)
- [x] No image compressed, blurred, or opacity changed
- [x] All choices maintain original position and order
- [x] Similarity score above 95% threshold
- [x] Engine reads only original_pdf artefact
- [x] Engine does not create project files
### Completion
- [x] STOP and wait for Specification 010

## Phase 10: Project Context Engine (Specification 010) ✅ COMPLETE
### Data Model
- [x] project_context/context_data.py — ProjectContext and all sub-dataclasses
- [x] project_context/blueprint_reader.py — BlueprintReader
- [x] project_context/validation_reader.py — ValidationReader
- [x] project_context/structure_reader.py — StructureReader
- [x] project_context/registry_reader.py — RegistryReader
- [x] project_context/file_plan_reader.py — FilePlanReader
- [x] project_context/dependency_reader.py — DependencyReader
### Helpers
- [x] project_context/context_assembler.py — ContextAssembler
- [x] project_context/context_linker.py — ContextLinker (O(1) indices)
- [x] project_context/context_validator.py — ContextValidator
### Engine
- [x] project_context/project_context_engine.py — ProjectContextEngine
- [x] project_context/__init__.py — exports
### Integration
- [x] Wire ProjectContextEngine into generators __init__.py
- [x] Wire ProjectContextEngine into bootstrap (priority 96, deps [dependency_resolver])
### Testing
- [x] Create comprehensive test script (tests/test_project_context.py)
- [x] Run tests and verify all pass
### Completion
- [x] STOP and wait for Specification 011

## Phase 11: Project Intelligence Graph Engine (Specification 011) ✅ COMPLETE
### Data Model
- [x] intelligence_graph/graph_data.py — ProjectIntelligenceGraph, GraphNode, GraphEdge, GraphFinding, GraphIndices, GraphProvenance, all 19 node-type constants, 12 edge-kind constants, category constants, severity constants
### Helpers
- [x] intelligence_graph/graph_builder.py — GraphBuilder (converts 7 artefacts into nodes + edges)
- [x] intelligence_graph/graph_navigator.py — GraphNavigator (O(1) lookup indices for fast traversal)
- [x] intelligence_graph/circular_detector.py — CircularDetector (circular deps, broken refs, unused, orphan, dead)
- [x] intelligence_graph/graph_validator.py — GraphValidator (internal consistency)
### Engine
- [x] intelligence_graph/intelligence_graph_engine.py — IntelligenceGraphEngine
- [x] intelligence_graph/__init__.py — exports
### Integration
- [x] Wire IntelligenceGraphEngine into generators __init__.py
- [x] Wire IntelligenceGraphEngine into bootstrap (priority 97, deps [project_context])
### Bug Fixes
- [x] Fix _DEPENDENCY_EDGE_KINDS: remove EDGE_REQUIRED_BY (reverse edge) to prevent false 2-cycles between component↔dependency pairs
- [x] Fix test helpers: use correct constructor signatures (FeatureUnit.build_priority, BlueprintValidationReport.quality, etc.)
- [x] Fix bootstrap test unpacking order (registry, orchestrator, manager)
- [x] Fix test assertions to match actual test data (feature names, component counts, dependency names, route/command counts)
- [x] Fix test_detector_dead_components: remove self-loop edge so dead node has no outgoing edges
### Testing
- [x] Create comprehensive test script (tests/test_intelligence_graph.py) — 127 tests across 13 sections
- [x] Run tests and verify all pass — 127/127 passed
### Completion
- [x] STOP and wait for Specification 012
