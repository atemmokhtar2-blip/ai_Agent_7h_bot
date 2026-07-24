"""
Registry reader (Specification 010).

The :class:`RegistryReader` extracts the information the Project Context
Engine needs from the ``component_registry`` artefact.  It reads
**only** the component registry and returns the component summaries,
component relationships, and build-order information that the
:class:`ContextAssembler` merges into the unified
:class:`ProjectContext`.

The reader does **not** write code, create files, or make build
decisions.  It is a pure extraction helper.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..component_detector.registry import (
    ComponentRegistry,
    DetectedComponent,
    ComponentDependencyEdge,
)
from .context_data import (
    ComponentSummary,
    RelationshipSummary,
    ExpansionPoint,
    SOURCE_COMPONENT_REGISTRY,
)


class RegistryReader:
    """Extract context-relevant data from the component registry.

    The reader is stateless.
    """

    def read(self, registry: ComponentRegistry) -> Dict[str, Any]:
        """Read the component registry and return the extracted parts.

        Returns a dict with keys:
            ``components`` — a list of :class:`ComponentSummary`.
            ``relationships`` — a list of :class:`RelationshipSummary`.
            ``expansion_points`` — a list of :class:`ExpansionPoint`.
            ``build_order_map`` — a dict mapping component name →
                build position.
            ``provenance_partial`` — a dict to update provenance.
        """
        return {
            "components": self._read_components(registry),
            "relationships": self._read_relationships(registry),
            "expansion_points": self._read_expansion_points(registry),
            "build_order_map": self._read_build_order_map(registry),
            "provenance_partial": {
                "component_registry_name": registry.project_name,
            },
        }

    # ------------------------------------------------------------------ #
    # Components
    # ------------------------------------------------------------------ #

    def _read_components(
        self, registry: ComponentRegistry,
    ) -> List[ComponentSummary]:
        summaries: List[ComponentSummary] = []
        for dc in registry.components:
            summaries.append(self._component_to_summary(dc))
        return summaries

    def _component_to_summary(
        self, dc: DetectedComponent,
    ) -> ComponentSummary:
        return ComponentSummary(
            name=dc.name,
            type=dc.type,
            purpose=dc.purpose,
            responsibility=dc.responsibility,
            source_feature=dc.source_feature,
            location=dc.location,
            build_order=dc.build_order,
            importance=dc.importance,
            files=[],
            dependencies=[],
            depends_on=list(dc.depends_on),
            depended_by=list(dc.depended_by),
            source_artefact=SOURCE_COMPONENT_REGISTRY,
        )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #

    def _read_relationships(
        self, registry: ComponentRegistry,
    ) -> List[RelationshipSummary]:
        summaries: List[RelationshipSummary] = []
        for edge in registry.relationships:
            summaries.append(RelationshipSummary(
                source=edge.source,
                target=edge.target,
                kind=edge.kind,
                description=edge.description,
                source_artefact=SOURCE_COMPONENT_REGISTRY,
            ))
        return summaries

    # ------------------------------------------------------------------ #
    # Expansion points
    # ------------------------------------------------------------------ #

    def _read_expansion_points(
        self, registry: ComponentRegistry,
    ) -> List[ExpansionPoint]:
        points: List[ExpansionPoint] = []
        for dc in registry.components:
            if dc.scalable:
                points.append(ExpansionPoint(
                    area=dc.name,
                    description=(
                        f"The {dc.name} component can be extended "
                        f"with additional sub-components or handlers."
                    ),
                    source_artefact=SOURCE_COMPONENT_REGISTRY,
                ))
        return points

    # ------------------------------------------------------------------ #
    # Build order map
    # ------------------------------------------------------------------ #

    def _read_build_order_map(
        self, registry: ComponentRegistry,
    ) -> Dict[str, int]:
        order_map: Dict[str, int] = {}
        for entry in registry.build_order:
            order_map[entry.component_name] = entry.position
        return order_map


__all__ = ["RegistryReader"]
