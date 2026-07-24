"""
Dependency reader (Specification 010).

The :class:`DependencyReader` extracts the information the Project
Context Engine needs from the ``dependency_resolution_report``
artefact.  It reads **only** the dependency resolution report and
returns the dependency summaries, dependency relationships, load-order
information, and findings that the :class:`ContextAssembler` merges
into the unified :class:`ProjectContext`.

The reader does **not** write code, create files, or make build
decisions.  It is a pure extraction helper.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..dependency_resolver.report_data import (
    DependencyResolutionReport,
    DependencyEntry,
    DependencyRelationship,
)
from .context_data import (
    DependencySummary,
    RelationshipSummary,
    ContextFinding,
    SOURCE_DEPENDENCY_REPORT,
    SEVERITY_WARNING,
)


class DependencyReader:
    """Extract context-relevant data from the dependency resolution
    report.

    The reader is stateless.
    """

    def read(
        self, report: DependencyResolutionReport,
    ) -> Dict[str, Any]:
        """Read the dependency resolution report and return the
        extracted parts.

        Returns a dict with keys:
            ``dependencies`` — a list of :class:`DependencySummary`.
            ``relationships`` — a list of :class:`RelationshipSummary`.
            ``findings`` — a list of :class:`ContextFinding`.
            ``load_order_map`` — a dict mapping dependency name →
                load position.
            ``provenance_partial`` — a dict to update provenance.
        """
        return {
            "dependencies": self._read_dependencies(report),
            "relationships": self._read_relationships(report),
            "findings": self._read_findings(report),
            "load_order_map": self._read_load_order_map(report),
            "provenance_partial": {
                "dependency_report_name": report.project_name,
            },
        }

    # ------------------------------------------------------------------ #
    # Dependencies
    # ------------------------------------------------------------------ #

    def _read_dependencies(
        self, report: DependencyResolutionReport,
    ) -> List[DependencySummary]:
        summaries: List[DependencySummary] = []
        for dep in report.dependencies:
            summaries.append(self._dependency_to_summary(dep))
        return summaries

    def _dependency_to_summary(
        self, dep: DependencyEntry,
    ) -> DependencySummary:
        return DependencySummary(
            name=dep.name,
            type=dep.type,
            suggested_version=dep.suggested_version,
            version_constraint=dep.version_constraint,
            reason=dep.reason,
            source_components=list(dep.source_components),
            priority=dep.priority,
            load_order=dep.load_order,
            language=dep.language,
            framework=dep.framework,
            depends_on=list(dep.depends_on),
            depended_by=list(dep.depended_by),
            source_artefact=SOURCE_DEPENDENCY_REPORT,
        )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #

    def _read_relationships(
        self, report: DependencyResolutionReport,
    ) -> List[RelationshipSummary]:
        summaries: List[RelationshipSummary] = []
        for rel in report.relationships:
            summaries.append(RelationshipSummary(
                source=rel.source,
                target=rel.target,
                kind=rel.kind,
                description=rel.description,
                source_artefact=SOURCE_DEPENDENCY_REPORT,
            ))
        return summaries

    # ------------------------------------------------------------------ #
    # Findings
    # ------------------------------------------------------------------ #

    def _read_findings(
        self, report: DependencyResolutionReport,
    ) -> List[ContextFinding]:
        findings: List[ContextFinding] = []
        for rf in report.findings:
            findings.append(ContextFinding(
                severity=rf.severity,
                code=rf.code,
                message=rf.message,
                affected=rf.affected,
                resolution_hint=rf.resolution_hint,
                category=rf.category,
            ))
        return findings

    # ------------------------------------------------------------------ #
    # Load order map
    # ------------------------------------------------------------------ #

    def _read_load_order_map(
        self, report: DependencyResolutionReport,
    ) -> Dict[str, int]:
        order_map: Dict[str, int] = {}
        for entry in report.load_order:
            order_map[entry.dependency_name] = entry.position
        return order_map


__all__ = ["DependencyReader"]
