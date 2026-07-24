"""
Requirement Intelligence Engine (Specification 012).

The :class:`RequirementIntelligenceEngine` is the engine responsible
for understanding the user's request with the highest possible
precision.  It does **not** write code, build the project, or choose
libraries.  Its sole function is to understand the user's intent and
convert it into precise, classified, prioritised, quality-validated
engineering requirements.

Data source
-----------
The engine reads **four** data sources from the generation context:

1. **User Request** — the raw user message (via the
   ``analysis_report`` artefact, or the raw ``context.request``).
2. **Project Context** — the ``project_context`` artefact produced by
   the
   :class:`~telegram_bot_engine.engines.generators.project_context.ProjectContextEngine`.
3. **Project Intelligence Graph** — the ``intelligence_graph``
   artefact produced by the
   :class:`~telegram_bot_engine.engines.generators.intelligence_graph.IntelligenceGraphEngine`.
4. **Knowledge Base** — the ``knowledge_base`` artefact, if present
   (a free-form dictionary of pre-approved assumptions and domain
   knowledge).

Responsibility
--------------
* Understand the user's intent across five dimensions (wants,
  does_not_want, final_goal, constraints, quality_level).
* Classify every requirement into one of nine categories.
* Detect missing information (and record required questions).
* Detect points of ambiguity.
* Detect conflicting, illogical, impossible, and duplicate
  requirements.
* Assign priorities based on importance, dependencies, and impact.
* Validate the quality rules (no requirement without description,
  goal, reason, and priority).
* Discover implicit requirements (those not explicitly stated but
  implied by the project).
* Record traceability (every requirement records its source
  artefact).
* Produce a :class:`RequirementIntelligenceReport` stored as the
  ``requirement_intelligence_report`` artefact.

What this engine does NOT do
----------------------------
* It does **not** write code.
* It does **not** create files on disk.
* It does **not** choose libraries.
* It does **not** make build decisions.

Output
------
The final output is a :class:`RequirementIntelligenceReport`, stored
in the context as the ``requirement_intelligence_report`` artefact.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from ....core.context import GenerationContext
from ....core.result import StageResult
from ...base.base_engine import BaseEngine
from .conflict_detector import ConflictDetector
from .context_reader import ContextData, ContextReader
from .graph_reader import GraphData, GraphReader
from .intent_analyzer import IntentAnalyzer
from .knowledge_reader import KnowledgeData, KnowledgeReader
from .missing_detector import MissingDetector
from .priority_assigner import PriorityAssigner
from .quality_validator import QualityValidator
from .report_assembler import ReportAssembler
from .report_data import (
    ReportFinding,
    RequirementIntelligenceReport,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)
from .request_reader import RequestData, RequestReader
from .requirement_classifier import RequirementClassifier


class RequirementIntelligenceEngine(BaseEngine):
    """The engine that understands the user's request and converts it
    into a Requirement Intelligence Report.

    This engine is the authority on *understanding* the user's intent.
    It reads the four data sources (user request, project context,
    intelligence graph, knowledge base), understands the intent across
    five dimensions, classifies every requirement into one of nine
    categories, detects missing information, ambiguities, and
    conflicts, assigns priorities, validates the quality rules,
    discovers implicit requirements, and produces the
    ``requirement_intelligence_report`` artefact.

    The engine does **not** write code, create files, choose
    libraries, or make build decisions.  Its sole function is to
    understand the user's intent and convert it into precise
    engineering requirements.
    """

    def __init__(self) -> None:
        super().__init__(
            name="requirement_intelligence",
            version="1.0.0",
            description=(
                "Understands the user's request with the highest "
                "possible precision and converts it into a "
                "Requirement Intelligence Report.  Reads the User "
                "Request, Project Context, Intelligence Graph, and "
                "Knowledge Base.  Performs intent analysis, "
                "requirement classification, missing-requirements "
                "detection, conflict detection, priority "
                "assignment, and quality validation.  Does not "
                "write code, create files, or make build decisions."
            ),
            tags=["generation", "understanding", "requirements"],
            metadata={"phase": "understanding"},
        )
        self._request_reader = RequestReader()
        self._context_reader = ContextReader()
        self._graph_reader = GraphReader()
        self._knowledge_reader = KnowledgeReader()
        self._intent_analyzer = IntentAnalyzer()
        self._classifier = RequirementClassifier()
        self._missing_detector = MissingDetector()
        self._conflict_detector = ConflictDetector()
        self._priority_assigner = PriorityAssigner()
        self._quality_validator = QualityValidator()
        self._assembler = ReportAssembler()

    # ----------------------------------------------------------------- #
    # Main entry point
    # ----------------------------------------------------------------- #

    def execute(self, context: GenerationContext) -> StageResult:
        """Build the Requirement Intelligence Report and produce the
        report artefact.

        Steps:
            1. Read the four data sources.
            2. Perform the intent analysis.
            3. Classify the requirements.
            4. Detect missing information and ambiguities.
            5. Detect conflicts.
            6. Assign priorities.
            7. Validate quality rules.
            8. Build provenance.
            9. Assemble the final report.
            10. Store the report in the generation context.
        """
        gen_start = time.perf_counter()

        # Step 1: read the four data sources.
        request = self._request_reader.read(context)
        context_data = self._context_reader.read(context)
        graph_data = self._graph_reader.read(context)
        knowledge_data = self._knowledge_reader.read(context)

        self._log.info(
            "Starting requirement intelligence",
            {
                "request_available": request.available,
                "context_available": context_data.available,
                "graph_available": graph_data.available,
                "knowledge_available": knowledge_data.available,
            },
        )

        # If no request data at all, we cannot proceed.
        if not request.available:
            report = self._build_empty_report(
                request, context_data, graph_data, knowledge_data,
            )
            context.set("requirement_intelligence_report", report)
            return self.failed(
                errors=[
                    "No user request data available. The Requirement "
                    "Intelligence Engine requires at least the user's "
                    "request to proceed."
                ],
                outputs={"requirement_intelligence_report": report},
            )

        # Step 2: perform the intent analysis.
        intent = self._intent_analyzer.analyze(
            request, context_data, graph_data, knowledge_data,
        )
        self._log.info(
            "Intent analysis complete",
            {
                "wants": bool(intent.wants),
                "does_not_want": bool(intent.does_not_want),
                "final_goal": bool(intent.final_goal),
                "quality_level": intent.quality_level,
                "confidence": intent.confidence,
            },
        )

        # Step 3: classify the requirements.
        requirements = self._classifier.classify(
            request, context_data, graph_data, knowledge_data,
        )
        self._log.info(
            "Requirements classified",
            {
                "requirement_count": len(requirements),
            },
        )

        # Step 4: detect missing information and ambiguities.
        questions, ambiguities = self._missing_detector.detect(
            request, context_data, graph_data, knowledge_data,
            requirements,
        )
        self._log.info(
            "Missing detection complete",
            {
                "questions": len(questions),
                "ambiguities": len(ambiguities),
            },
        )

        # Step 5: detect conflicts.
        conflicts = self._conflict_detector.detect(
            requirements, context_data, graph_data,
        )
        self._log.info(
            "Conflict detection complete",
            {
                "conflicts": len(conflicts),
            },
        )

        # Step 6: assign priorities.
        self._priority_assigner.assign(
            requirements, request, context_data, knowledge_data,
        )
        self._log.info(
            "Priorities assigned",
            {
                "critical": sum(
                    1 for r in requirements if r.priority == "critical"
                ),
                "high": sum(
                    1 for r in requirements if r.priority == "high"
                ),
                "normal": sum(
                    1 for r in requirements if r.priority == "normal"
                ),
                "low": sum(
                    1 for r in requirements if r.priority == "low"
                ),
            },
        )

        # Step 7: build provenance.
        provenance = self._assembler.build_provenance(
            request, context_data, graph_data, knowledge_data,
        )

        # Step 8: assemble the report (without quality validation
        # first, then validate).
        report = self._assembler.assemble(
            intent=intent,
            requirements=requirements,
            questions=questions,
            ambiguities=ambiguities,
            conflicts=conflicts,
            quality_violations=[],
            findings=[],
            provenance=provenance,
            request=request,
            context=context_data,
            graph=graph_data,
            knowledge=knowledge_data,
        )

        # Step 9: validate quality rules.
        quality_violations, quality_findings = (
            self._quality_validator.validate(report)
        )
        report.quality_violations = quality_violations
        report.findings.extend(quality_findings)

        # Rebuild summary and warnings after quality validation.
        report.summary = self._assembler._build_summary(report)
        report.warnings = self._assembler._collect_warnings(report)

        self._log.info(
            "Quality validation complete",
            {
                "violations": len(quality_violations),
                "findings": len(quality_findings),
            },
        )

        # Step 10: store the report in the generation context.
        context.set("requirement_intelligence_report", report)
        context.metadata["requirement_intelligence"] = report

        total_duration_ms = (time.perf_counter() - gen_start) * 1000

        self._log.info(
            "Requirement intelligence complete",
            {
                "requirement_count": report.requirement_count,
                "question_count": report.question_count,
                "ambiguity_count": report.ambiguity_count,
                "conflict_count": report.conflict_count,
                "quality_violation_count": report.quality_violation_count,
                "error_count": report.error_count,
                "warning_count": report.warning_count,
                "ready": report.ready,
                "duration_ms": round(total_duration_ms, 2),
            },
        )

        # Separate errors and warnings.
        error_findings = [
            f for f in report.findings
            if f.severity == SEVERITY_ERROR
        ]
        warning_findings = [
            f for f in report.findings
            if f.severity == SEVERITY_WARNING
        ]

        if error_findings or report.quality_violations:
            error_messages = [
                f"[{f.code}] {f.message}" for f in error_findings
            ]
            for v in report.quality_violations:
                if v.severity == SEVERITY_ERROR:
                    error_messages.append(v.message)
            return self.failed(
                errors=error_messages,
                outputs={"requirement_intelligence_report": report},
                warnings=report.warnings,
            )

        return self.ok(
            outputs={"requirement_intelligence_report": report},
            metadata={
                "requirement_count": report.requirement_count,
                "question_count": report.question_count,
                "ambiguity_count": report.ambiguity_count,
                "conflict_count": report.conflict_count,
                "quality_violation_count": report.quality_violation_count,
                "error_count": report.error_count,
                "warning_count": report.warning_count,
                "ready": report.ready,
                "duration_ms": round(total_duration_ms, 2),
            },
        )

    # ----------------------------------------------------------------- #
    # Helpers
    # ----------------------------------------------------------------- #

    def _build_empty_report(
        self,
        request: RequestData,
        context_data: ContextData,
        graph_data: GraphData,
        knowledge_data: KnowledgeData,
    ) -> RequirementIntelligenceReport:
        """Build an empty report when no request data is available."""
        provenance = self._assembler.build_provenance(
            request, context_data, graph_data, knowledge_data,
        )
        report = RequirementIntelligenceReport(
            provenance=provenance,
        )
        report.add_finding(
            severity=SEVERITY_ERROR,
            code="no_request_data",
            message=(
                "No user request data was available for the "
                "Requirement Intelligence Engine to process."
            ),
            affected="request",
            resolution_hint=(
                "Provide a user request for the engine to understand."
            ),
            category="quality",
        )
        report.summary = self._assembler._build_summary(report)
        report.notes = self._assembler._build_notes(
            report, request, context_data, graph_data, knowledge_data,
        )
        report.warnings = self._assembler._collect_warnings(report)
        return report


__all__ = ["RequirementIntelligenceEngine"]
