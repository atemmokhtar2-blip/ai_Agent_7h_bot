"""
Project Context Engine (Specification 010).

The :class:`ProjectContextEngine` is the engine responsible for
building the complete, authoritative, unified understanding of the
entire project **before** any code is written or any file is created
on disk.  It does **not** write code, create files, or make build
decisions.  Its sole function is to merge the six upstream artefacts
into a single, validated :class:`ProjectContext` — the single
authoritative context that every downstream engine can query for any
piece of project information.

Data source
-----------
The engine reads **only** six artefacts from the generation context:

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

It is **forbidden** from reading the user's request.

Responsibility
--------------
* Merge all six upstream artefacts into a single unified model.
* Build the context graph (Feature → Component → File → Dependency →
  Stage) with precomputed O(1) look-up indices.
* Validate the context for internal consistency.
* Record traceability (every piece of information records its source
  artefact).
* Produce a :class:`ProjectContext` stored as the
  ``project_context`` artefact.

What this engine does NOT do
----------------------------
* It does **not** write code.
* It does **not** create files on disk.
* It does **not** make build decisions.
* It does **not** read the user's request.

Output
------
The final output is a :class:`ProjectContext`, stored in the context
as the ``project_context`` artefact.
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
from ..project_planner.blueprint import ProjectBlueprint
from ..structure_generator.structure_map import ProjectStructureMap
from .context_assembler import ContextAssembler
from .context_data import (
    ProjectContext,
    ContextFinding,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SEVERITY_INFO,
)
from .context_linker import ContextLinker
from .context_validator import ContextValidator


class ProjectContextEngine(BaseEngine):
    """The engine that builds the unified project context.

    This engine is the authority on the *complete understanding* of
    the project.  It reads the six upstream artefacts (project
    blueprint, blueprint validation report, project structure map,
    component registry, file generation plan, and dependency
    resolution report), merges them into a single
    :class:`ProjectContext`, builds the context graph with O(1)
    look-up indices, validates the context for internal consistency,
    and produces the ``project_context`` artefact.

    The engine is forbidden from reading the user's request, writing
    code, creating files, or making build decisions.
    """

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

    # ----------------------------------------------------------------- #
    # Main entry point
    # ----------------------------------------------------------------- #

    def execute(self, context: GenerationContext) -> StageResult:
        """Build the unified project context and produce the context
        artefact.

        Steps:
            1. Obtain the six artefacts from the context.
            2. Type-check the artefacts.
            3. Assemble the context (merge all six artefacts).
            4. Build the context graph (link indices).
            5. Validate the context for internal consistency.
            6. Build the summary and notes.
            7. Store the context in the generation context.
        """
        gen_start = time.perf_counter()

        # Step 1: obtain the six artefacts.
        blueprint = context.get("project_blueprint")
        if blueprint is None:
            return self.failed([
                "No 'project_blueprint' artefact found. The "
                "Project Context Engine requires the Project "
                "Planning Engine to have run first."
            ])

        validation_report = context.get("blueprint_validation_report")
        if validation_report is None:
            return self.failed([
                "No 'blueprint_validation_report' artefact found. "
                "The Project Context Engine requires the "
                "Blueprint Validator Engine to have run first."
            ])

        structure_map = context.get("project_structure_map")
        if structure_map is None:
            return self.failed([
                "No 'project_structure_map' artefact found. The "
                "Project Context Engine requires the Structure "
                "Generation Engine to have run first."
            ])

        registry = context.get("component_registry")
        if registry is None:
            return self.failed([
                "No 'component_registry' artefact found. The "
                "Project Context Engine requires the Component "
                "Detection Engine to have run first."
            ])

        file_plan = context.get("file_generation_plan")
        if file_plan is None:
            return self.failed([
                "No 'file_generation_plan' artefact found. The "
                "Project Context Engine requires the File "
                "Generation Planning Engine to have run first."
            ])

        dependency_report = context.get("dependency_resolution_report")
        if dependency_report is None:
            return self.failed([
                "No 'dependency_resolution_report' artefact found. "
                "The Project Context Engine requires the "
                "Dependency Resolution Engine to have run first."
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

        self._log.info(
            "Starting project context assembly",
            {
                "blueprint_name": blueprint.identity.name,
                "features": len(blueprint.features),
                "components": registry.component_count,
                "structure_files": len(structure_map.files),
                "file_plan_files": file_plan.file_count,
                "dependencies": dependency_report.dependency_count,
                "validation_status": validation_report.status,
            },
        )

        # Step 3: assemble the context (merge all six artefacts).
        project_context = self._assembler.assemble(
            blueprint=blueprint,
            validation_report=validation_report,
            structure_map=structure_map,
            registry=registry,
            file_plan=file_plan,
            dependency_report=dependency_report,
        )
        self._log.info(
            "Context assembled",
            {
                "features": project_context.feature_count,
                "components": project_context.component_count,
                "files": project_context.file_count,
                "dependencies": project_context.dependency_count,
                "stages": project_context.stage_count,
                "relationships": project_context.relationship_count,
            },
        )

        # Step 4: build the context graph (link indices).
        self._linker.link(project_context)
        self._log.info(
            "Context graph built",
            {
                "links": project_context.link_count,
                "feature_to_components": len(
                    project_context.indices.feature_to_components
                ),
                "component_to_files": len(
                    project_context.indices.component_to_files
                ),
                "file_to_dependencies": len(
                    project_context.indices.file_to_dependencies
                ),
            },
        )

        # Step 5: validate the context for internal consistency.
        validation_findings = self._validator.validate(project_context)
        project_context.findings.extend(validation_findings)
        self._log.info(
            "Context validation complete",
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

        # Step 6: build the summary and notes.
        total_duration_ms = (time.perf_counter() - gen_start) * 1000
        project_context.summary = self._build_summary(
            project_context, total_duration_ms,
        )
        project_context.notes = self._build_notes(
            project_context, validation_report,
        )

        # Collect warnings from findings.
        project_context.warnings = [
            f.message for f in project_context.findings
            if f.severity == SEVERITY_WARNING
        ]

        # Step 7: store the context in the generation context.
        context.set("project_context", project_context)
        context.metadata["project_context"] = project_context

        # Separate errors and warnings from all findings.
        error_findings = [
            f for f in project_context.findings
            if f.severity == SEVERITY_ERROR
        ]
        warning_findings = [
            f for f in project_context.findings
            if f.severity == SEVERITY_WARNING
        ]

        self._log.info(
            "Project context complete",
            {
                "project_name": project_context.goal.name,
                "features": project_context.feature_count,
                "components": project_context.component_count,
                "files": project_context.file_count,
                "dependencies": project_context.dependency_count,
                "stages": project_context.stage_count,
                "links": project_context.link_count,
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
                outputs={"project_context": project_context},
                warnings=project_context.warnings,
            )

        return self.ok(
            outputs={"project_context": project_context},
            metadata={
                "project_name": project_context.goal.name,
                "feature_count": project_context.feature_count,
                "component_count": project_context.component_count,
                "file_count": project_context.file_count,
                "dependency_count": project_context.dependency_count,
                "stage_count": project_context.stage_count,
                "link_count": project_context.link_count,
                "relationship_count": project_context.relationship_count,
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
        context: ProjectContext,
        duration_ms: float,
    ) -> str:
        """Build a human-readable summary of the project context."""
        return (
            f"Built project context with "
            f"{context.feature_count} feature(s), "
            f"{context.component_count} component(s), "
            f"{context.file_count} file(s), "
            f"{context.dependency_count} dependency(ies), "
            f"{context.stage_count} stage(s), "
            f"{context.relationship_count} relationship(s), and "
            f"{context.link_count} context link(s). "
            f"{context.error_count} error(s), "
            f"{context.warning_count} warning(s). "
            f"Generated in {round(duration_ms, 2)} ms."
        )

    @staticmethod
    def _build_notes(
        context: ProjectContext,
        validation_report: BlueprintValidationReport,
    ) -> List[str]:
        """Build the notes list for the project context."""
        return [
            f"Project context generated at "
            f"{datetime.now(timezone.utc).isoformat()}.",
            f"Source blueprint: "
            f"{context.provenance.blueprint_name or 'unnamed'}.",
            f"Validation status: "
            f"{context.provenance.validation_status or 'unknown'}.",
            f"Source structure map: "
            f"{context.provenance.structure_map_name or 'unnamed'}.",
            f"Source component registry: "
            f"{context.provenance.component_registry_name or 'unnamed'}.",
            f"Source file generation plan: "
            f"{context.provenance.file_plan_name or 'unnamed'}.",
            f"Source dependency resolution report: "
            f"{context.provenance.dependency_report_name or 'unnamed'}.",
            f"All sources used: "
            f"{', '.join(context.provenance.all_sources_used)}.",
        ]


__all__ = ["ProjectContextEngine"]
