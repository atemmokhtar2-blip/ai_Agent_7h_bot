"""
Report assembler — assembles the final Requirement Intelligence Report.

The :class:`ReportAssembler` is the final step of the requirement
intelligence pipeline.  It takes the :class:`IntentAnalysis`, the list
of :class:`Requirement` objects, the list of
:class:`RequiredQuestion` objects, the list of
:class:`AmbiguityPoint` objects, the list of
:class:`RequirementConflict` objects, the list of
:class:`QualityViolation` objects, and the :class:`ReportProvenance`
and assembles them into the final
:class:`RequirementIntelligenceReport`.

The assembler also:
* Builds the human-readable summary.
* Builds the notes list.
* Collects warnings from all sources.
* Merges all findings into the report.

The assembler does **not** write code, create files, or make build
decisions.  It only *assembles* the report.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from .context_reader import ContextData
from .graph_reader import GraphData
from .knowledge_reader import KnowledgeData
from .report_data import (
    IntentAnalysis,
    QualityViolation,
    ReportFinding,
    ReportProvenance,
    Requirement,
    RequirementConflict,
    RequirementIntelligenceReport,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SOURCE_INTELLIGENCE_GRAPH,
    SOURCE_KNOWLEDGE_BASE,
    SOURCE_PROJECT_CONTEXT,
    SOURCE_USER_REQUEST,
)
from .request_reader import RequestData


class ReportAssembler:
    """Assembles the final Requirement Intelligence Report.

    The assembler takes all the pieces produced by the other helpers
    (intent analysis, requirements, questions, ambiguities, conflicts,
    quality violations, provenance) and assembles them into a single
    :class:`RequirementIntelligenceReport`.

    The assembler is the only component that creates the
    :class:`RequirementIntelligenceReport` — all other helpers produce
    their individual pieces.
    """

    def assemble(
        self,
        intent: IntentAnalysis,
        requirements: List[Requirement],
        questions: list,
        ambiguities: list,
        conflicts: List[RequirementConflict],
        quality_violations: List[QualityViolation],
        findings: List[ReportFinding],
        provenance: ReportProvenance,
        request: RequestData,
        context: ContextData,
        graph: GraphData,
        knowledge: KnowledgeData,
    ) -> RequirementIntelligenceReport:
        """Assemble the final report from all the pieces."""
        report = RequirementIntelligenceReport(
            intent=intent,
            requirements=requirements,
            required_questions=questions,
            ambiguities=ambiguities,
            conflicts=conflicts,
            quality_violations=quality_violations,
            findings=findings,
            provenance=provenance,
        )

        # Build the summary.
        report.summary = self._build_summary(report)
        report.notes = self._build_notes(
            report, request, context, graph, knowledge,
        )

        # Collect warnings.
        report.warnings = self._collect_warnings(report)

        return report

    # ----------------------------------------------------------------- #
    # Summary
    # ----------------------------------------------------------------- #

    @staticmethod
    def _build_summary(report: RequirementIntelligenceReport) -> str:
        """Build a human-readable summary of the report."""
        return (
            f"Requirement Intelligence Report: "
            f"{report.requirement_count} requirement(s) "
            f"({report.explicit_count} explicit, "
            f"{report.implicit_count} implicit), "
            f"{report.question_count} required question(s), "
            f"{report.ambiguity_count} ambiguity point(s), "
            f"{report.conflict_count} conflict(s), "
            f"{report.quality_violation_count} quality violation(s). "
            f"Intent confidence: {report.intent.confidence:.1%}. "
            f"Quality level: {report.intent.quality_level}. "
            f"{'Report is ready.' if report.ready else 'Report is not ready.'}"
        )

    # ----------------------------------------------------------------- #
    # Notes
    # ----------------------------------------------------------------- #

    @staticmethod
    def _build_notes(
        report: RequirementIntelligenceReport,
        request: RequestData,
        context: ContextData,
        graph: GraphData,
        knowledge: KnowledgeData,
    ) -> List[str]:
        """Build the notes list for the report."""
        notes: List[str] = [
            f"Requirement Intelligence Report generated at "
            f"{datetime.now(timezone.utc).isoformat()}.",
            f"Data sources used: "
            f"{', '.join(report.provenance.all_sources_used)}.",
            f"User request available: {report.provenance.request_available}.",
            f"Project context available: "
            f"{report.provenance.project_context_available}.",
            f"Intelligence graph available: "
            f"{report.provenance.intelligence_graph_available}.",
            f"Knowledge base available: "
            f"{report.provenance.knowledge_base_available}.",
        ]

        if context.available:
            notes.append(
                f"Project name from context: "
                f"{context.project_name or 'unknown'}."
            )

        if graph.available:
            notes.append(
                f"Intelligence graph: {graph.node_count} node(s), "
                f"{graph.edge_count} edge(s)."
            )

        if knowledge.available:
            notes.append(
                f"Knowledge base keys: "
                f"{', '.join(knowledge.keys) if knowledge.keys else 'none'}."
            )

        if report.requirement_count > 0:
            notes.append(
                f"Requirements by category: "
                f"{report.category_counts()}."
            )
            notes.append(
                f"Requirements by priority: "
                f"{report.priority_counts()}."
            )
            notes.append(
                f"Requirements by source: "
                f"{report.source_counts()}."
            )

        return notes

    # ----------------------------------------------------------------- #
    # Warnings
    # ----------------------------------------------------------------- #

    @staticmethod
    def _collect_warnings(
        report: RequirementIntelligenceReport,
    ) -> List[str]:
        """Collect all warnings from the report."""
        warnings: List[str] = []

        # Warnings from findings.
        for finding in report.findings:
            if finding.severity == SEVERITY_WARNING:
                warnings.append(f"[{finding.code}] {finding.message}")

        # Warnings from conflicts.
        for conflict in report.conflicts:
            if conflict.severity == SEVERITY_WARNING:
                warnings.append(
                    f"[conflict:{conflict.kind}] {conflict.description}"
                )

        # Warnings from quality violations.
        for violation in report.quality_violations:
            if violation.severity == SEVERITY_WARNING:
                warnings.append(violation.message)

        return warnings

    # ----------------------------------------------------------------- #
    # Provenance builder
    # ----------------------------------------------------------------- #

    @staticmethod
    def build_provenance(
        request: RequestData,
        context: ContextData,
        graph: GraphData,
        knowledge: KnowledgeData,
    ) -> ReportProvenance:
        """Build the provenance record from the data sources."""
        sources_used: List[str] = []
        if request.available:
            sources_used.append(SOURCE_USER_REQUEST)
        if context.available:
            sources_used.append(SOURCE_PROJECT_CONTEXT)
        if graph.available:
            sources_used.append(SOURCE_INTELLIGENCE_GRAPH)
        if knowledge.available:
            sources_used.append(SOURCE_KNOWLEDGE_BASE)

        request_summary = (
            (request.cleaned_request or request.raw_request)[:200]
            if request.available else ""
        )

        return ReportProvenance(
            request_available=request.available,
            project_context_available=context.available,
            intelligence_graph_available=graph.available,
            knowledge_base_available=knowledge.available,
            all_sources_used=sources_used,
            request_summary=request_summary,
            context_project_name=(
                context.project_name if context.available else ""
            ),
            graph_node_count=(
                graph.node_count if graph.available else 0
            ),
            knowledge_base_keys=(
                knowledge.keys if knowledge.available else []
            ),
        )


__all__ = ["ReportAssembler"]
