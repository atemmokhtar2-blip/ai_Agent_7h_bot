"""
Blueprint reader (Specification 010).

The :class:`BlueprintReader` extracts the information the Project Context
Engine needs from the ``project_blueprint`` artefact.  It reads **only**
the blueprint and returns a set of plain data containers that the
:class:`ContextAssembler` can merge into the unified
:class:`ProjectContext`.

The reader does **not** write code, create files, or make build
decisions.  It is a pure extraction helper: given a
:class:`ProjectBlueprint`, it returns:

* the :class:`ProjectGoal` (high-level project identity),
* the list of :class:`FeatureSummary` objects,
* the list of :class:`RelationshipSummary` objects (component
  relationships),
* the list of :class:`ExecutionStage` objects (from the execution
  plan),
* the list of :class:`ExpansionPoint` objects (from the structure
  entries and component kinds).

Every item is tagged with ``source_artefact = SOURCE_BLUEPRINT`` so
that the traceability requirement is satisfied.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..project_planner.blueprint import (
    ProjectBlueprint,
    InternalComponent,
    ComponentRelationship,
)
from ..project_planner.feature_unit import FeatureUnit
from ..project_planner.execution_plan import ExecutionPlan, ExecutionPhase
from .context_data import (
    ProjectGoal,
    FeatureSummary,
    RelationshipSummary,
    ExecutionStage,
    ExpansionPoint,
    SOURCE_BLUEPRINT,
)


class BlueprintReader:
    """Extract context-relevant data from the project blueprint.

    The reader is stateless — a new instance can be created for each
    call or a single instance can be reused across calls.
    """

    def read(self, blueprint: ProjectBlueprint) -> Dict[str, Any]:
        """Read the blueprint and return the extracted context parts.

        Returns a dict with keys:
            ``goal``        — a :class:`ProjectGoal`.
            ``features``    — a list of :class:`FeatureSummary`.
            ``relationships`` — a list of :class:`RelationshipSummary`.
            ``stages``      — a list of :class:`ExecutionStage`.
            ``expansion_points`` — a list of :class:`ExpansionPoint`.
        """
        return {
            "goal": self._read_goal(blueprint),
            "features": self._read_features(blueprint),
            "relationships": self._read_relationships(blueprint),
            "stages": self._read_stages(blueprint),
            "expansion_points": self._read_expansion_points(blueprint),
        }

    # ------------------------------------------------------------------ #
    # Goal
    # ------------------------------------------------------------------ #

    def _read_goal(self, blueprint: ProjectBlueprint) -> ProjectGoal:
        identity = blueprint.identity
        primary_goal = ""
        if blueprint.features:
            descriptions = [
                f.description for f in blueprint.features
                if f.description
            ]
            if descriptions:
                primary_goal = (
                    f"A {identity.bot_type} Telegram bot with "
                    f"{len(blueprint.features)} feature(s)."
                )
            else:
                primary_goal = (
                    f"A {identity.bot_type} Telegram bot."
                )
        else:
            primary_goal = (
                f"A {identity.bot_type} Telegram bot."
            )

        return ProjectGoal(
            name=identity.name,
            display_name=identity.display_name or identity.name,
            bot_type=identity.bot_type,
            primary_goal=primary_goal,
            language=identity.language,
            language_version=identity.language_version,
            framework=identity.framework,
            database=identity.database,
            source_artefact=SOURCE_BLUEPRINT,
        )

    # ------------------------------------------------------------------ #
    # Features
    # ------------------------------------------------------------------ #

    def _read_features(
        self, blueprint: ProjectBlueprint,
    ) -> List[FeatureSummary]:
        summaries: List[FeatureSummary] = []
        for fu in blueprint.features:
            components = list(fu.introduces_components)
            summaries.append(FeatureSummary(
                name=fu.name,
                display_name=fu.display_name or fu.name,
                description=fu.description,
                priority=fu.build_priority,
                source_feature=fu.source_feature or fu.name,
                components=components,
                source_artefact=SOURCE_BLUEPRINT,
            ))
        return summaries

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #

    def _read_relationships(
        self, blueprint: ProjectBlueprint,
    ) -> List[RelationshipSummary]:
        summaries: List[RelationshipSummary] = []
        for rel in blueprint.relationships:
            summaries.append(RelationshipSummary(
                source=rel.source,
                target=rel.target,
                kind=rel.kind,
                description=rel.description,
                source_artefact=SOURCE_BLUEPRINT,
            ))
        return summaries

    # ------------------------------------------------------------------ #
    # Execution stages
    # ------------------------------------------------------------------ #

    def _read_stages(
        self, blueprint: ProjectBlueprint,
    ) -> List[ExecutionStage]:
        plan: ExecutionPlan = blueprint.execution_plan
        stages: List[ExecutionStage] = []
        for phase in plan.phases:
            stages.append(ExecutionStage(
                name=phase.name,
                phase=phase.number,
                priority=phase.number * 100,
                components=list(phase.components),
                files=[],
                dependencies=[],
                source_artefact=SOURCE_BLUEPRINT,
            ))
        return stages

    # ------------------------------------------------------------------ #
    # Expansion points
    # ------------------------------------------------------------------ #

    def _read_expansion_points(
        self, blueprint: ProjectBlueprint,
    ) -> List[ExpansionPoint]:
        points: List[ExpansionPoint] = []
        seen: set = set()

        # From the structure entries — directories are natural
        # expansion points.
        for entry in blueprint.structure.entries:
            if entry.kind == "directory" and entry.path:
                if entry.path not in seen:
                    seen.add(entry.path)
                    points.append(ExpansionPoint(
                        area=entry.path,
                        description=(
                            entry.description
                            or f"The {entry.path} directory can be "
                               f"extended with additional modules."
                        ),
                        source_artefact=SOURCE_BLUEPRINT,
                    ))

        # From the component kinds — feature components are
        # expansion points.
        for comp in blueprint.components:
            if comp.kind == "feature" and comp.name:
                key = f"component:{comp.name}"
                if key not in seen:
                    seen.add(key)
                    points.append(ExpansionPoint(
                        area=comp.name,
                        description=(
                            f"The {comp.name} feature component can "
                            f"be extended with additional handlers "
                            f"or services."
                        ),
                        source_artefact=SOURCE_BLUEPRINT,
                    ))

        return points


__all__ = ["BlueprintReader"]
