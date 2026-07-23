"""
Core Request Analyzer Engine — the first engine in the pipeline.

This engine performs a comprehensive 10-stage analysis of the user's
request and produces an :class:`AnalysisReport` — the single,
authoritative description of what the user wants.

The analysis is **pure** — no code is generated, no files are created.
The report is stored in the generation context as the ``analysis_report``
artefact for downstream engines to read.

Stages (executed in order):
    1. Text cleaning — normalise whitespace, remove noise.
    2. Text segmentation — sentences, tokens, language detection.
    3. Keyword extraction — category-tagged keyword matches.
    4. Request classification — bot type detection and ordering.
    5. Feature extraction — independent, atomic features.
    6. Technology extraction — languages, libraries, databases, frameworks.
    7. Relationship analysis — dependencies between entities.
    8. Conflict detection — contradictory or ambiguous choices.
    9. Missing information detection — questions for the user.
    10. Final report assembly — confidence scores and readiness.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ....core.context import GenerationContext
from ....core.result import StageResult
from ...base.base_engine import BaseEngine
from .analysis_report import AnalysisReport
from . import stages as st


class AnalyzerEngine(BaseEngine):
    """The Core Request Analyzer — produces an :class:`AnalysisReport`.

    This engine runs all 10 analysis stages sequentially, accumulating
    results in a shared state dictionary and the :class:`AnalysisReport`
    data model.  The final report is stored in the generation context as
    the ``analysis_report`` artefact.
    """

    def __init__(self) -> None:
        super().__init__(
            name="analyzer",
            version="2.0.0",
            description=(
                "Performs a 10-stage analysis of the user request, producing "
                "an AnalysisReport that serves as the authoritative reference "
                "for all downstream engines."
            ),
            tags=["understanding", "analysis"],
            metadata={"phase": "understanding", "stage_count": 10},
        )

    # -- stage list ---------------------------------------------------------

    def _stages(self) -> List[tuple]:
        """Return the ordered list of (stage_name, stage_fn) pairs."""
        return [
            ("cleaner", st.stage1_clean),
            ("segmenter", st.stage2_segment),
            ("keyword_extractor", st.stage3_keywords),
            ("classifier", st.stage4_classify),
            ("feature_extractor", st.stage5_features),
            ("technology_extractor", st.stage6_technologies),
            ("relationship_analyzer", st.stage7_relationships),
            ("conflict_detector", st.stage8_conflicts),
            ("missing_info_detector", st.stage9_missing_info),
            ("report_builder", st.stage10_report),
        ]

    # -- main entry ---------------------------------------------------------

    def execute(self, context: GenerationContext) -> StageResult:
        """Run all 10 analysis stages and produce an AnalysisReport."""
        raw_request = context.request
        if not raw_request or not raw_request.strip():
            return self.failed(
                ["Empty request — nothing to analyze."],
                warnings=["The request was empty or whitespace-only."],
            )

        self._log.info(
            "Starting analysis",
            {"request_length": len(raw_request)},
        )

        # Shared mutable state passed through all stages
        state: Dict[str, Any] = {"raw_request": raw_request}

        # The report — all stages write into this object
        report = AnalysisReport()

        all_warnings: List[str] = []

        for stage_name, stage_fn in self._stages():
            try:
                stage_warnings = stage_fn(state, report)
                if stage_warnings:
                    all_warnings.extend(stage_warnings)

                self._log.debug(
                    f"Stage '{stage_name}' completed",
                    {"warnings": len(stage_warnings)},
                )
            except Exception as exc:
                error_msg = f"Stage '{stage_name}' failed: {exc}"
                self._log.error(error_msg)
                return self.failed(
                    [error_msg],
                    warnings=all_warnings,
                )

        # Store the report in the context for downstream engines
        context.set("analysis_report", report)

        # Also store the AnalysisReport directly on context metadata
        # for easy access by the blueprint composer
        context.metadata["analysis_report"] = report

        self._log.info(
            "Analysis complete",
            {
                "bot_type": report.primary_bot_type.type if report.primary_bot_type else None,
                "features": len(report.features),
                "technologies": len(report.technologies),
                "ready": report.ready,
                "warnings": len(all_warnings),
            },
        )

        # Build outputs
        outputs: Dict[str, Any] = {
            "analysis_report": report,
            "bot_type": report.primary_bot_type.type if report.primary_bot_type else "general",
            "features": [f.name for f in report.features],
            "technologies": [t.name for t in report.technologies],
            "ready": report.ready,
        }

        return self.ok(
            outputs=outputs,
            metadata={
                "stage_count": 10,
                "completed_stages": [s[0] for s in self._stages()],
                "warnings": all_warnings,
                "has_conflicts": report.has_conflicts,
                "has_missing_required": report.has_missing_required_info,
            },
        )


__all__ = ["AnalyzerEngine"]
