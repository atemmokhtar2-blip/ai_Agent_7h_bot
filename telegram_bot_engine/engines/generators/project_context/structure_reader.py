"""
Structure reader (Specification 010).

The :class:`StructureReader` extracts the information the Project Context
Engine needs from the ``project_structure_map`` artefact.  It reads
**only** the structure map and returns the file summaries, structure
relationships, build-order information, and expansion points that the
:class:`ContextAssembler` merges into the unified
:class:`ProjectContext`.

The reader does **not** write code, create files, or make build
decisions.  It is a pure extraction helper.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..structure_generator.structure_map import (
    ProjectStructureMap,
    FileEntry,
    StructureRelationship,
    BuildOrderEntry,
)
from .context_data import (
    FileSummary,
    RelationshipSummary,
    ExpansionPoint,
    SOURCE_STRUCTURE,
)


class StructureReader:
    """Extract context-relevant data from the structure map.

    The reader is stateless.
    """

    def read(self, structure_map: ProjectStructureMap) -> Dict[str, Any]:
        """Read the structure map and return the extracted parts.

        Returns a dict with keys:
            ``files`` — a list of :class:`FileSummary`.
            ``relationships`` — a list of :class:`RelationshipSummary`.
            ``expansion_points`` — a list of :class:`ExpansionPoint`.
            ``build_order_map`` — a dict mapping file path → build
                position (for ordering).
            ``provenance_partial`` — a dict to update provenance.
        """
        return {
            "files": self._read_files(structure_map),
            "relationships": self._read_relationships(structure_map),
            "expansion_points": self._read_expansion_points(structure_map),
            "build_order_map": self._read_build_order_map(structure_map),
            "provenance_partial": {
                "structure_map_name": structure_map.project_name,
            },
        }

    # ------------------------------------------------------------------ #
    # Files
    # ------------------------------------------------------------------ #

    def _read_files(
        self, structure_map: ProjectStructureMap,
    ) -> List[FileSummary]:
        summaries: List[FileSummary] = []
        for fe in structure_map.files:
            summaries.append(self._file_entry_to_summary(fe))
        return summaries

    def _file_entry_to_summary(self, fe: FileEntry) -> FileSummary:
        return FileSummary(
            name=fe.name,
            path=fe.path,
            file_type=fe.file_type,
            purpose=fe.purpose,
            folder=fe.folder,
            responsible_engine=fe.building_engine,
            generation_priority=fe.build_order,
            build_order=fe.build_order,
            source_component=fe.source_component,
            depends_on=[],
            depended_by=[],
            reason_for_existence=fe.purpose,
            contains_code=fe.contains_code,
            source_artefact=SOURCE_STRUCTURE,
        )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #

    def _read_relationships(
        self, structure_map: ProjectStructureMap,
    ) -> List[RelationshipSummary]:
        summaries: List[RelationshipSummary] = []
        for folder in structure_map.folders:
            for rel in folder.relationships:
                summaries.append(RelationshipSummary(
                    source=rel.source,
                    target=rel.target,
                    kind=rel.kind,
                    description=rel.description,
                    source_artefact=SOURCE_STRUCTURE,
                ))
        for fe in structure_map.files:
            for rel in fe.relationships:
                summaries.append(RelationshipSummary(
                    source=rel.source,
                    target=rel.target,
                    kind=rel.kind,
                    description=rel.description,
                    source_artefact=SOURCE_STRUCTURE,
                ))
        return summaries

    # ------------------------------------------------------------------ #
    # Expansion points
    # ------------------------------------------------------------------ #

    def _read_expansion_points(
        self, structure_map: ProjectStructureMap,
    ) -> List[ExpansionPoint]:
        points: List[ExpansionPoint] = []
        for folder in structure_map.folders:
            if folder.scalable:
                points.append(ExpansionPoint(
                    area=folder.path or folder.name,
                    description=(
                        folder.reason
                        or f"The {folder.name} folder can be "
                           f"extended with additional files."
                    ),
                    source_artefact=SOURCE_STRUCTURE,
                ))
        return points

    # ------------------------------------------------------------------ #
    # Build order map
    # ------------------------------------------------------------------ #

    def _read_build_order_map(
        self, structure_map: ProjectStructureMap,
    ) -> Dict[str, int]:
        order_map: Dict[str, int] = {}
        for entry in structure_map.build_order:
            order_map[entry.path] = entry.position
        return order_map


__all__ = ["StructureReader"]
