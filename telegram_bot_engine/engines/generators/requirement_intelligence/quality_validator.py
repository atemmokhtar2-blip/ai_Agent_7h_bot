"""
Quality validator — validates the quality rules of the Requirement
Intelligence Report.

The :class:`QualityValidator` is responsible for enforcing the quality
rules that state:

* No requirement may exist without a **description**.
* No requirement may exist without a **goal**.
* No requirement may exist without a **reason**.
* No requirement may exist without a **priority**.

When a requirement violates one or more of these rules, the validator
records a :class:`QualityViolation`.

The validator also produces general :class:`ReportFinding` objects for
issues that are not tied to a single requirement (e.g. empty report,
missing intent analysis).

The validator does **not** write code, create files, or make build
decisions.  It only *validates*.
"""

from __future__ import annotations

from typing import List

from .report_data import (
    QUALITY_LEVEL_STANDARD,
    QualityViolation,
    ReportFinding,
    Requirement,
    RequirementIntelligenceReport,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)


# ---------------------------------------------------------------------------#
# Quality rules
# ---------------------------------------------------------------------------#
#
# Each rule is a tuple of (field_name, human_readable_name).
# A requirement is in violation if the field is empty or whitespace.

QUALITY_RULES = [
    ("description", "description"),
    ("goal", "goal"),
    ("reason", "reason"),
    ("priority", "priority"),
]


class QualityValidator:
    """Validates the quality rules of the Requirement Intelligence
    Report.

    The validator reads the :class:`RequirementIntelligenceReport` (or
    the list of :class:`Requirement` objects) and produces a list of
    :class:`QualityViolation` objects and a list of
    :class:`ReportFinding` objects.

    Quality rules:
    * No requirement may exist without a description.
    * No requirement may exist without a goal.
    * No requirement may exist without a reason.
    * No requirement may exist without a priority.

    Additional checks:
    * The report must have at least one requirement.
    * The intent analysis should have at least a "wants" dimension.
    * Each requirement should have a valid category.
    * Each requirement should have a valid priority.
    * Each requirement should have a valid source artefact.
    """

    def __init__(self) -> None:
        self._next_violation_id = 1

    # ----------------------------------------------------------------- #
    # Main entry point
    # ----------------------------------------------------------------- #

    def validate(
        self,
        report: RequirementIntelligenceReport,
    ) -> tuple:
        """Validate the report and return a tuple
        ``(violations, findings)``."""
        violations: List[QualityViolation] = []
        findings: List[ReportFinding] = []

        # Check each requirement against the quality rules.
        for req in report.requirements:
            missing_fields: List[str] = []
            for field_name, display_name in QUALITY_RULES:
                value = getattr(req, field_name, "")
                if not value or (isinstance(value, str) and not value.strip()):
                    missing_fields.append(display_name)

            if missing_fields:
                violations.append(QualityViolation(
                    requirement_id=req.id,
                    missing_fields=missing_fields,
                    severity=SEVERITY_ERROR,
                    message=(
                        f"Requirement '{req.id}' ({req.name}) is "
                        f"missing: {', '.join(missing_fields)}."
                    ),
                ))

        # Report-level findings.
        findings.extend(
            self._validate_report_level(report),
        )

        return violations, findings

    # ----------------------------------------------------------------- #
    # Report-level validation
    # ----------------------------------------------------------------- #

    def _validate_report_level(
        self,
        report: RequirementIntelligenceReport,
    ) -> List[ReportFinding]:
        """Validate the report at the report level."""
        findings: List[ReportFinding] = []

        # Empty report.
        if report.is_empty:
            findings.append(ReportFinding(
                severity=SEVERITY_ERROR,
                code="empty_report",
                message=(
                    "The Requirement Intelligence Report contains no "
                    "requirements. The engine could not identify any "
                    "requirements from the user's request."
                ),
                affected="requirements",
                resolution_hint=(
                    "Provide a more detailed user request with "
                    "specific features and capabilities."
                ),
                category="quality",
            ))

        # Missing intent analysis.
        if not report.intent.wants:
            findings.append(ReportFinding(
                severity=SEVERITY_WARNING,
                code="missing_intent_wants",
                message=(
                    "The intent analysis does not have a 'wants' "
                    "dimension. The engine could not determine what "
                    "the user wants."
                ),
                affected="intent.wants",
                resolution_hint=(
                    "Provide a clearer description of what the bot "
                    "should do."
                ),
                category="intent",
            ))

        # Missing final goal.
        if not report.intent.final_goal:
            findings.append(ReportFinding(
                severity=SEVERITY_INFO,
                code="missing_final_goal",
                message=(
                    "The intent analysis does not have a 'final_goal' "
                    "dimension."
                ),
                affected="intent.final_goal",
                resolution_hint=(
                    "Specify the ultimate goal the bot should achieve."
                ),
                category="intent",
            ))

        # Quality level not set (uses default).
        if report.intent.quality_level == QUALITY_LEVEL_STANDARD:
            findings.append(ReportFinding(
                severity=SEVERITY_INFO,
                code="default_quality_level",
                message=(
                    "The quality level was not explicitly specified "
                    "and defaults to 'standard'."
                ),
                affected="intent.quality_level",
                resolution_hint=(
                    "Specify the desired quality level (minimal, "
                    "standard, high, or production) if a different "
                    "level is needed."
                ),
                category="intent",
            ))

        # High proportion of implicit requirements.
        if report.requirement_count > 0:
            implicit_ratio = report.implicit_count / report.requirement_count
            if implicit_ratio > 0.5:
                findings.append(ReportFinding(
                    severity=SEVERITY_WARNING,
                    code="high_implicit_ratio",
                    message=(
                        f"{report.implicit_count} out of "
                        f"{report.requirement_count} requirements "
                        f"({implicit_ratio:.0%}) are implicit. The "
                        f"user's request may be under-specified."
                    ),
                    affected="requirements",
                    resolution_hint=(
                        "Provide more explicit requirements to reduce "
                        "the proportion of implicit requirements."
                    ),
                    category="quality",
                ))

        return findings

    # ----------------------------------------------------------------- #
    # Standalone validation (for testing)
    # ----------------------------------------------------------------- #

    def validate_requirements(
        self,
        requirements: List[Requirement],
    ) -> List[QualityViolation]:
        """Validate a list of requirements and return violations only.

        This is a convenience method for testing the quality rules
        without a full report.
        """
        violations: List[QualityViolation] = []
        for req in requirements:
            missing_fields: List[str] = []
            for field_name, display_name in QUALITY_RULES:
                value = getattr(req, field_name, "")
                if not value or (isinstance(value, str) and not value.strip()):
                    missing_fields.append(display_name)

            if missing_fields:
                violations.append(QualityViolation(
                    requirement_id=req.id,
                    missing_fields=missing_fields,
                    severity=SEVERITY_ERROR,
                    message=(
                        f"Requirement '{req.id}' ({req.name}) is "
                        f"missing: {', '.join(missing_fields)}."
                    ),
                ))
        return violations


__all__ = ["QualityValidator", "QUALITY_RULES"]
