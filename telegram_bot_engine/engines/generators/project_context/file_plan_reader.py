"""
File plan reader (Specification 010).

The :class:`FilePlanReader` extracts the information the Project Context
Engine needs from the ``file_generation_plan`` artefact.  It reads
**only** the file plan and returns the file summaries, file
relationships, and build-order information that the
:class:`ContextAssembler` merges into the unified
:class:`ProjectContext`.

The reader does **not** write code, create files, or make build
decisions.  It is a pure extraction helper.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..file_planner.plan_data import (
    FileGenerationPlan,
    FilePlanEntry,
    FileRelationship,
)
from .context_data import (
    FileSummary,
    RelationshipSummary,
    ExpansionPoint,
    SOURCE_FILE_PLAN,
)


class FilePlanReader:
    """Extract context-relevant data from the file generation plan.

    The reader is stateless.
    """

    def read(self, file_plan: FileGenerationPlan) -> Dict[str, Any]:
        """Read the file plan and return the extracted parts.

        Returns a dict with keys:
            ``files`` — a list of :class:`FileSummary`.
            ``relationships`` — a list of :class:`RelationshipSummary`.
            ``expansion_points`` — a list of :class:`ExpansionPoint`.
            ``build_order_map`` — a dict mapping file path → build
                position.
            ``provenance_partial`` — a dict to update provenance.
        """
        return {
            "files": self._read_files(file_plan),
            "relationships": self._read_relationships(file_plan),
            "expansion_points": self._read_expansion_points(file_plan),
            "build_order_map": self._read_build_order_map(file_plan),
            "provenance_partial": {
                "file_plan_name": file_plan.project_name,
            },
        }

    # ------------------------------------------------------------------ #
    # Files
    # ------------------------------------------------------------------ #

    def _read_files(
        self, file_plan: FileGenerationPlan,
    ) -> List[FileSummary]:
        summaries: List[FileSummary] = []
        for fpe in file_plan.files:
            summaries.append(self._plan_entry_to_summary(fpe))
        return summaries

    def _plan_entry_to_summary(self, fpe: FilePlanEntry) -> FileSummary:
        return FileSummary(
            name=fpe.name,
            path=fpe.path,
            file_type=fpe.file_type,
            purpose=fpe.purpose,
            folder=fpe.folder,
            responsible_engine=fpe.responsible_engine,
            generation_priority=fpe.generation_priority,
            build_order=fpe.build_order,
            source_component=fpe.source_component,
            depends_on=list(fpe.depends_on),
            depended_by=list(fpe.depended_by),
            reason_for_existence=(
                fpe.reason_for_existence or fpe.purpose
            ),
            contains_code=fpe.contains_code,
            source_artefact=SOURCE_FILE_PLAN,
        )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #

    def _read_relationships(
        self, file_plan: FileGenerationPlan,
    ) -> List[RelationshipSummary]:
        summaries: List[RelationshipSummary] = []
        for rel in file_plan.relationships:
            summaries.append(RelationshipSummary(
                source=rel.source,
                target=rel.target,
                kind=rel.kind,
                description=rel.description,
                source_artefact=SOURCE_FILE_PLAN,
            ))
        return summaries

    # ------------------------------------------------------------------ #
    # Expansion points
    # ------------------------------------------------------------------ #

    def _read_expansion_points(
        self, file_plan: FileGenerationPlan,
    ) -> List[ExpansionPoint]:
        points: List[ExpansionPoint] = []
        for fpe in file_plan.files:
            if fpe.scalable:
                points.append(ExpansionPoint(
                    area=fpe.path,
                    description=(
                        f"The file {fpe.name} can be extended "
                        f"with additional functions or classes."
                    ),
                    source_artefact=SOURCE_FILE_PLAN,
                ))
        return points

    # ------------------------------------------------------------------ #
    # Build order map
    # ------------------------------------------------------------------ #

    def _read_build_order_map(
        self, file_plan: FileGenerationPlan,
    ) -> Dict[str, int]:
        order_map: Dict[str, int] = {}
        for entry in file_plan.generation_order:
            order_map[entry.file_path] = entry.position
        return order_map


__all__ = ["FilePlanReader"]
