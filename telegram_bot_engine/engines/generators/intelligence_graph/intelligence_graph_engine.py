"""
Intelligence Graph Engine (Specification 011).

The :class:`IntelligenceGraphEngine` is the engine responsible for
building the complete, authoritative, intelligent graph of the entire
project **before** any code is written or any file is created on
disk.  It does **not** write code, create files, or make build
decisions.  Its sole function is to convert the seven upstream
artefacts into a single, navigable
:class:`ProjectIntelligenceGraph` — the single reference point that
every downstream engine can query for any piece of project
information and reach any element in very few steps.

Data source
-----------
The engine reads **seven** artefacts from the generation context:

1. ``project_blueprint`` — produced by the
   :class:`~telegram_bot_engine.engines.generators.project_planner.ProjectPlanningEngine`.
2. ``blueprint_validation_report`` — produced by the
   :class:`~telegram_bot_engine.engines.generators.blueprint_validator.BlueprintValidatorEngine`.
3. ``project_structure_map`` — produced by the
   :class:`~telegram_bot_engine.engines.generators.structure_generator.StructureGenerationEngine`.
4. ``component_registry`` — produced by the
   :class:`~telegram_bot_engine.engines.generators.component_detector.ComponentDetectionEngine`.
5. ``file_generation_plan`` — produced by the
   :class:`~telegram_bot_engine.engines.generators.file_planner.FileGenerationPlanningEngine`.
6. ``dependency_resolution_report`` — produced by the
   :class:`~telegram_bot_engine.engines.generators.dependency_resolver.DependencyResolutionEngine`.
7. ``project_context`` — produced by the
   :class:`~telegram_bot_engine.engines.generators.project_context.ProjectContextEngine`.

It is **forbidden** from reading the user's request.

Responsibility
--------------
* Convert all seven upstream artefacts into a single intelligent graph
  of nodes (19 types) and edges (12 kinds).
* Build the O(1) look-up indices so that any downstream engine can
  navigate the graph in constant time.
* Detect circular dependencies, broken references, unused components,
  orphan files, and dead components.
* Validate the graph for internal consistency.
* Record traceability (every node and edge records its source
  artefact).
* Produce a :class:`ProjectIntelligenceGraph` stored as the
  ``intelligence_graph`` artefact.

What this engine does NOT do
----------------------------
* It does **not** write code.
* It does **not** create files on disk.
* It does **not** make build decisions.
* It does **not** read the user's request.

Output
------
The final output is a :class:`ProjectIntelligenceGraph`, stored in
the context as the ``intelligence_graph`` artefact.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from ....core.context import GenerationContext
from ....core.result import StageResult
from ...base.base_engine import BaseEngine
from ..blueprint_validator.validation_report import (
    BlueprintValidationReport,
)
from ..component_detector.registry import ComponentRegistry
from ..dependency_resolver.report_data import DependencyResolutionReport
from ..file_planner.plan_data import FileGenerationPlan
from ..project_context.context_data import ProjectContext
from ..project_planner.blueprint import ProjectBlueprint
from ..structure_generator.structure_map import ProjectStructureMap
from .graph_builder import GraphBuilder
from .graph_navigator import GraphNavigator
from .circular_detector import CircularDetector
from .graph_validator import GraphValidator
from .graph_data import (
    ProjectIntelligenceGraph,
    GraphFinding,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SEVERITY_INFO,
    ALL_SOURCES,
)


class IntelligenceGraphEngine(BaseEngine):
    """The engine that builds the intelligent project graph.

    This engine is the authority on the *complete graph* of the
    project.  It reads the seven upstream artefacts (project
    blueprint, blueprint validation report, project structure map,
    component registry, file generation plan, dependency resolution
    report, and project context), converts them into a single
    :class:`ProjectIntelligenceGraph` with 19 node types and 12 edge
    kinds, builds the O(1) look-up indices, detects circular
    dependencies and other structural problems, validates the graph
    for internal consistency, and produces the
    ``intelligence_graph`` artefact.

    The engine is forbidden from reading the user's request, writing
    code, creating files, or making build decisions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="intelligence_graph",
            version="1.0.0",
            description=(
                "Builds the complete, intelligent project graph "
                "by converting the Project Blueprint, Blueprint "
                "Validation Report, Project Structure Map, "
                "Component Registry, File Generation Plan, "
                "Dependency Resolution Report, and Project "
                "Context into a single Project Intelligence "
                "Graph with 19 node types and 12 edge kinds.  "
                "Produces O(1) look-up indices for fast "
                "navigation.  Detects circular dependencies, "
                "broken references, unused components, orphan "
                "files, and dead components.  Does not write "
                "code, create files, or make build decisions."
            ),
            tags=["generation", "graph", "navigation"],
            metadata={"phase": "build_graph"},
        )
        self._builder = GraphBuilder()
        self._navigator = GraphNavigator()
        self._circular_detector = CircularDetector()
        self._validator = GraphValidator()

    # ----------------------------------------------------------------- #
    # Main entry point
    # ----------------------------------------------------------------- #

    def execute(self, context: GenerationContext) -> StageResult:
        """Build the intelligence graph and produce the graph
        artefact.

        Steps:
            1. Obtain the seven artefacts from the context.
            2. Type-check the artefacts.
            3. Build the graph (convert all seven artefacts into
               nodes and edges).
            4. Build the O(1) look-up indices (navigate the graph).
            5. Detect circular dependencies and structural problems.
            6. Validate the graph for internal consistency.
            7. Build the summary and notes.
            8. Store the graph in the generation context.
        """
        gen_start = time.perf_counter()

        # Step 1: obtain the seven artefacts.
        blueprint = context.get("project_blueprint")
        if blueprint is None:
            return self.failed([
                "No 'project_blueprint' artefact found. The "
                "Intelligence Graph Engine requires the Project "
                "Planning Engine to have run first."
            ])

        validation_report = context.get("blueprint_validation_report")
        if validation_report is None:
            return self.failed([
                "No 'blueprint_validation_report' artefact found. "
                "The Intelligence Graph Engine requires the "
                "Blueprint Validator Engine to have run first."
            ])

        structure_map = context.get("project_structure_map")
        if structure_map is None:
            return self.failed([
                "No 'project_structure_map' artefact found. The "
                "Intelligence Graph Engine requires the Structure "
                "Generation Engine to have run first."
            ])

        registry = context.get("component_registry")
        if registry is None:
            return self.failed([
                "No 'component_registry' artefact found. The "
                "Intelligence Graph Engine requires the "
                "Component Detection Engine to have run first."
            ])

        file_plan = context.get("file_generation_plan")
        if file_plan is None:
            return self.failed([
                "No 'file_generation_plan' artefact found. The "
                "Intelligence Graph Engine requires the File "
                "Generation Planning Engine to have run first."
            ])

        dependency_report = context.get("dependency_resolution_report")
        if dependency_report is None:
            return self.failed([
                "No 'dependency_resolution_report' artefact "
                "found. The Intelligence Graph Engine requires "
                "the Dependency Resolution Engine to have run "
                "first."
            ])

        project_context = context.get("project_context")
        if project_context is None:
            return self.failed([
                "No 'project_context' artefact found. The "
                "Intelligence Graph Engine requires the Project "
                "Context Engine to have run first."
            ])

        # Step 2: type-check the artefacts.
        if not isinstance(blueprint, ProjectBlueprint):
            return self.failed([
                "The 'project_blueprint' artefact is not a "
                "ProjectBlueprint instance."
            ])
        if not isinstance(validation_report, BlueprintValidationReport):
            return self.failed([
                "The 'blueprint_validation_report' artefact is "
                "not a BlueprintValidationReport instance."
            ])
        if not isinstance(structure_map, ProjectStructureMap):
            return self.failed([
                "The 'project_structure_map' artefact is not a "
                "ProjectStructureMap instance."
            ])
        if not isinstance(registry, ComponentRegistry):
            return self.failed([
                "The 'component_registry' artefact is not a "
                "ComponentRegistry instance."
            ])
        if not isinstance(file_plan, FileGenerationPlan):
            return self.failed([
                "The 'file_generation_plan' artefact is not a "
                "FileGenerationPlan instance."
            ])
        if not isinstance(dependency_report, DependencyResolutionReport):
            return self.failed([
                "The 'dependency_resolution_report' artefact is "
                "not a DependencyResolutionReport instance."
            ])
        if not isinstance(project_context, ProjectContext):
            return self.failed([
                "The 'project_context' artefact is not a "
                "ProjectContext instance."
            ])

        self._log.info(
            "Starting intelligence graph construction",
            {
                "project_name": blueprint.identity.name,
                "features": len(blueprint.features),
                "components": registry.component_count,
                "structure_files": len(structure_map.files),
                "file_plan_files": file_plan.file_count,
                "dependencies": dependency_report.dependency_count,
                "context_features": project_context.feature_count,
                "context_components": project_context.component_count,
            },
        )

        # Step 3: build the graph (convert all seven artefacts into
        # nodes and edges).
        graph = self._builder.build(
            blueprint=blueprint,
            validation_report=validation_report,
            structure_map=structure_map,
            registry=registry,
            file_plan=file_plan,
            dependency_report=dependency_report,
            project_context=project_context,
        )
        self._log.info(
            "Graph built (nodes and edges)",
            {
                "nodes": graph.node_count,
                "edges": graph.edge_count,
            },
        )

        # Step 4: build the O(1) look-up indices (navigate the graph).
        self._navigator.navigate(graph)
        self._log.info(
            "Graph indices built",
            {
                "node_types": graph.node_type_count,
                "edge_kinds": graph.edge_kind_count,
            },
        )

        # Step 5: detect circular dependencies and structural problems.
        detection_findings = self._circular_detector.detect(graph)
        for finding in detection_findings:
            graph.add_finding(
                severity=finding.severity,
                code=finding.code,
                message=finding.message,
                affected=finding.affected,
                category=finding.category,
                resolution_hint=finding.resolution_hint,
                cycle=finding.cycle,
            )
        self._log.info(
            "Circular detection complete",
            {
                "detection_findings": len(detection_findings),
                "errors": sum(
                    1 for f in detection_findings
                    if f.severity == SEVERITY_ERROR
                ),
                "warnings": sum(
                    1 for f in detection_findings
                    if f.severity == SEVERITY_WARNING
                ),
                "info": sum(
                    1 for f in detection_findings
                    if f.severity == SEVERITY_INFO
                ),
            },
        )

        # Step 6: validate the graph for internal consistency.
        validation_findings = self._validator.validate(graph)
        for finding in validation_findings:
            graph.add_finding(
                severity=finding.severity,
                code=finding.code,
                message=finding.message,
                affected=finding.affected,
                category=finding.category,
                resolution_hint=finding.resolution_hint,
                cycle=finding.cycle,
            )
        self._log.info(
            "Graph validation complete",
            {
                "validation_findings": len(validation_findings),
                "errors": sum(
                    1 for f in validation_findings
                    if f.severity == SEVERITY_ERROR
                ),
                "warnings": sum(
                    1 for f in validation_findings
                    if f.severity == SEVERITY_WARNING
                ),
            },
        )

        # Step 7: build the summary and notes.
        total_duration_ms = (time.perf_counter() - gen_start) * 1000
        graph.summary = self._build_summary(graph, total_duration_ms)
        graph.notes = self._build_notes(graph)
        graph.warnings = [
            f.message for f in graph.findings
            if f.severity == SEVERITY_WARNING
        ]

        # Step 8: store the graph in the generation context.
        context.set("intelligence_graph", graph)
        context.metadata["intelligence_graph"] = graph

        # Separate errors and warnings from all findings.
        error_findings = [
            f for f in graph.findings
            if f.severity == SEVERITY_ERROR
        ]
        warning_findings = [
            f for f in graph.findings
            if f.severity == SEVERITY_WARNING
        ]

        self._log.info(
            "Intelligence graph complete",
            {
                "project_name": blueprint.identity.name,
                "nodes": graph.node_count,
                "edges": graph.edge_count,
                "node_types": graph.node_type_count,
                "edge_kinds": graph.edge_kind_count,
                "findings": graph.finding_count,
                "errors": len(error_findings),
                "warnings": len(warning_findings),
                "duration_ms": round(total_duration_ms, 2),
            },
        )

        if error_findings:
            error_messages = [
                f"[{f.code}] {f.message}" for f in error_findings
            ]
            return self.failed(
                errors=error_messages,
                outputs={"intelligence_graph": graph},
                warnings=graph.warnings,
            )

        return self.ok(
            outputs={"intelligence_graph": graph},
            metadata={
                "project_name": blueprint.identity.name,
                "node_count": graph.node_count,
                "edge_count": graph.edge_count,
                "node_type_count": graph.node_type_count,
                "edge_kind_count": graph.edge_kind_count,
                "finding_count": graph.finding_count,
                "error_count": len(error_findings),
                "warning_count": len(warning_findings),
                "duration_ms": round(total_duration_ms, 2),
            },
        )

    # ----------------------------------------------------------------- #
    # Helpers
    # ----------------------------------------------------------------- #

    @staticmethod
    def _build_summary(
        graph: ProjectIntelligenceGraph,
        duration_ms: float,
    ) -> str:
        """Build a human-readable summary of the intelligence graph."""
        return (
            f"Built intelligence graph with "
            f"{graph.node_count} node(s) across "
            f"{graph.node_type_count} type(s) and "
            f"{graph.edge_count} edge(s) across "
            f"{graph.edge_kind_count} kind(s). "
            f"{graph.finding_count} finding(s): "
            f"{graph.error_count} error(s), "
            f"{graph.warning_count} warning(s). "
            f"Generated in {round(duration_ms, 2)} ms."
        )

    @staticmethod
    def _build_notes(
        graph: ProjectIntelligenceGraph,
    ) -> List[str]:
        """Build the notes list for the intelligence graph."""
        notes: List[str] = [
            f"Intelligence graph generated at "
            f"{datetime.now(timezone.utc).isoformat()}.",
            f"Project name: "
            f"{graph.provenance.project_name or 'unnamed'}.",
            f"Source blueprint: "
            f"{graph.provenance.blueprint_name or 'unnamed'}.",
            f"Validation status: "
            f"{graph.provenance.validation_status or 'unknown'}.",
            f"Source structure map: "
            f"{graph.provenance.structure_map_name or 'unnamed'}.",
            f"Source component registry: "
            f"{graph.provenance.component_registry_name or 'unnamed'}.",
            f"Source file generation plan: "
            f"{graph.provenance.file_plan_name or 'unnamed'}.",
            f"Source dependency resolution report: "
            f"{graph.provenance.dependency_report_name or 'unnamed'}.",
            f"Source project context: "
            f"{graph.provenance.project_context_name or 'unnamed'}.",
            f"All sources used: "
            f"{', '.join(graph.provenance.all_sources_used)}.",
        ]
        return notes


__all__ = ["IntelligenceGraphEngine"]
