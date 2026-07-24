"""
Validation reader (Specification 010).

The :class:`ValidationReader` extracts the information the Project
Context Engine needs from the ``blueprint_validation_report``
artefact.  It reads **only** the validation report and returns the
validation status, quality scores, and any findings that the
:class:`ContextAssembler` needs to record in the unified
:class:`ProjectContext`.

The reader does **not** write code, create files, or make build
decisions.  It is a pure extraction helper.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..blueprint_validator.validation_report import (
    BlueprintValidationReport,
    STATUS_APPROVED,
    STATUS_REJECTED,
)
from .context_data import (
    ContextFinding,
    SourceProvenance,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SEVERITY_INFO,
    SOURCE_VALIDATION,
)


class ValidationReader:
    """Extract context-relevant data from the validation report.

    The reader is stateless.
    """

    def read(
        self, report: BlueprintValidationReport,
    ) -> Dict[str, Any]:
        """Read the validation report and return the extracted parts.

        Returns a dict with keys:
            ``validation_status`` — the approval status string.
            ``quality_scores`` — a dict of the quality sub-scores.
            ``overall_quality`` — the overall quality score.
            ``findings`` — a list of :class:`ContextFinding` objects.
            ``provenance_partial`` — a dict to update provenance.
        """
        return {
            "validation_status": report.status,
            "quality_scores": self._extract_quality_scores(report),
            "overall_quality": (
                report.quality.overall if report.quality else 0.0
            ),
            "findings": self._extract_findings(report),
            "provenance_partial": {
                "validation_status": report.status,
            },
        }

    # ------------------------------------------------------------------ #
    # Quality scores
    # ------------------------------------------------------------------ #

    def _extract_quality_scores(
        self, report: BlueprintValidationReport,
    ) -> Dict[str, float]:
        quality = report.quality
        if quality is None:
            return {}
        return {
            "structure_quality": quality.structure_quality,
            "dependency_quality": quality.dependency_quality,
            "feature_quality": quality.feature_quality,
            "planning_quality": quality.planning_quality,
            "overall": quality.overall,
            "minimum_required": quality.minimum_required,
        }

    # ------------------------------------------------------------------ #
    # Findings
    # ------------------------------------------------------------------ #

    def _extract_findings(
        self, report: BlueprintValidationReport,
    ) -> List[ContextFinding]:
        findings: List[ContextFinding] = []

        # From the layer results.
        for layer_id, layer_result in report.layers.items():
            for vf in layer_result.findings:
                findings.append(ContextFinding(
                    severity=vf.severity,
                    code=vf.code or f"layer_{layer_id}",
                    message=vf.message,
                    affected=vf.affected,
                    resolution_hint=vf.resolution_hint,
                    category="validation",
                ))

        # From the conflicts.
        for conflict in report.conflicts:
            findings.append(ContextFinding(
                severity=conflict.severity,
                code="conflict",
                message=conflict.description,
                affected=conflict.affected,
                resolution_hint=conflict.resolution_hint,
                category="consistency",
            ))

        # From the errors list.
        for err in report.errors:
            findings.append(ContextFinding(
                severity=err.severity if hasattr(err, "severity") else SEVERITY_ERROR,
                code=err.code if hasattr(err, "code") else "validation_error",
                message=err.message if hasattr(err, "message") else str(err),
                affected=err.affected if hasattr(err, "affected") else "",
                resolution_hint=(
                    err.resolution_hint
                    if hasattr(err, "resolution_hint") else ""
                ),
                category="validation",
            ))

        # From the warnings list.
        for warn in report.warnings:
            findings.append(ContextFinding(
                severity=warn.severity if hasattr(warn, "severity") else SEVERITY_WARNING,
                code=warn.code if hasattr(warn, "code") else "validation_warning",
                message=warn.message if hasattr(warn, "message") else str(warn),
                affected=warn.affected if hasattr(warn, "affected") else "",
                resolution_hint=(
                    warn.resolution_hint
                    if hasattr(warn, "resolution_hint") else ""
                ),
                category="validation",
            ))

        # From the missing info list.
        for missing in report.missing_info:
            findings.append(ContextFinding(
                severity=(
                    SEVERITY_ERROR if missing.required else SEVERITY_WARNING
                ),
                code="missing_information",
                message=missing.description,
                affected=missing.field,
                resolution_hint=missing.question,
                category="validation",
            ))

        return findings


__all__ = ["ValidationReader"]
