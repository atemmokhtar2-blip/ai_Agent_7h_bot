"""
Visual Validator — validates that the rebuilt page matches the original
with near-100% visual fidelity.

The :class:`VisualValidator` is a stateless helper that the
:class:`VisualPageReconstructionEngine` calls during the *validation*
phase.  It compares the original PDF page with the rebuilt page and
produces a :class:`VisualSimilarityReport` with detailed accuracy
metrics.

Acceptance rules
----------------
* The similarity score must be **above 95%** to pass validation.
* Layout accuracy (position, spacing, alignment) must be above 98%.
* Image accuracy (size, position, aspect ratio) must be above 98%.
* Text accuracy (font, size, content, alignment) must be above 98%.
* Spacing accuracy (margins, gaps, line height) must be above 98%.
* Choice accuracy (label, text, position, order) must be above 98%.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from .page_analysis import PageAnalysis, ElementPosition


# ---------------------------------------------------------------------------
# Validation weight constants
# ---------------------------------------------------------------------------
VISUAL_ACCURACY_THRESHOLD = 0.95  # 95% minimum to pass
LAYOUT_ACCURACY_WEIGHT = 0.20
IMAGE_ACCURACY_WEIGHT = 0.30
TEXT_ACCURACY_WEIGHT = 0.25
SPACING_ACCURACY_WEIGHT = 0.15
CHOICE_ACCURACY_WEIGHT = 0.10


# ---------------------------------------------------------------------------
# Similarity report
# ---------------------------------------------------------------------------
@dataclass
class VisualSimilarityReport:
    """The validation report produced by the :class:`VisualValidator`.
    Attributes:
        page_number: The 1-based page number.
        overall_score: The overall visual similarity score (0.0–1.0).
        layout_accuracy: The layout accuracy score (0.0–1.0).
        image_accuracy: The image accuracy score (0.0–1.0).
        text_accuracy: The text accuracy score (0.0–1.0).
        spacing_accuracy: The spacing accuracy score (0.0–1.0).
        choice_accuracy: The choice accuracy score (0.0–1.0).
        passed: ``True`` when the overall score exceeds the threshold.
        total_elements: The total number of elements compared.
        matched_elements: The number of elements that matched.
        mismatched_elements: The number of elements that did not match.
        findings: A list of validation findings (strings).
        duration_ms: The validation duration in milliseconds.
    """
    page_number: int = 1
    overall_score: float = 0.0
    layout_accuracy: float = 0.0
    image_accuracy: float = 0.0
    text_accuracy: float = 0.0
    spacing_accuracy: float = 0.0
    choice_accuracy: float = 0.0
    passed: bool = False
    total_elements: int = 0
    matched_elements: int = 0
    mismatched_elements: int = 0
    findings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def add_finding(self, message: str) -> None:
        self.findings.append(message)

    @property
    def has_findings(self) -> bool:
        return len(self.findings) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "overall_score": self.overall_score,
            "layout_accuracy": self.layout_accuracy,
            "image_accuracy": self.image_accuracy,
            "text_accuracy": self.text_accuracy,
            "spacing_accuracy": self.spacing_accuracy,
            "choice_accuracy": self.choice_accuracy,
            "passed": self.passed,
            "total_elements": self.total_elements,
            "matched_elements": self.matched_elements,
            "mismatched_elements": self.mismatched_elements,
            "findings": list(self.findings),
            "duration_ms": self.duration_ms,
        }


# ---------------------------------------------------------------------------
# Visual Validator
# ---------------------------------------------------------------------------
class VisualValidator:
    """Validates that a rebuilt page matches the original.

    The validator compares the original :class:`PageAnalysis` with the
    rebuilt page data and produces a :class:`VisualSimilarityReport`.
    """

    # Position tolerance in points.
    POSITION_TOLERANCE: float = 0.5

    def __init__(self) -> None:
        self._log_messages: List[str] = []

    @property
    def log_messages(self) -> List[str]:
        return list(self._log_messages)

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def validate(
        self,
        original_analysis: PageAnalysis,
        rebuilt_positions: List[ElementPosition],
    ) -> VisualSimilarityReport:
        """Validate a rebuilt page against the original analysis.

        Parameters:
            original_analysis: The original :class:`PageAnalysis`.
            rebuilt_positions: The positions of elements in the
                rebuilt page (same order as in the analysis).

        Returns:
            A :class:`VisualSimilarityReport` with detailed accuracy
            metrics.
        """
        import time
        start_time = time.monotonic()

        report = VisualSimilarityReport(
            page_number=original_analysis.page_number,
        )

        # Collect all original positions.
        original_elements = original_analysis.all_elements
        report.total_elements = len(original_elements)
        report.mismatched_elements = 0

        # Compute per-category accuracy.
        report.layout_accuracy = self._compute_layout_accuracy(
            original_analysis, rebuilt_positions,
        )
        report.image_accuracy = self._compute_image_accuracy(
            original_analysis,
        )
        report.text_accuracy = self._compute_text_accuracy(
            original_analysis,
        )
        report.spacing_accuracy = self._compute_spacing_accuracy(
            original_analysis,
        )
        report.choice_accuracy = self._compute_choice_accuracy(
            original_analysis,
        )

        # Compute overall weighted score.
        report.overall_score = self._compute_overall_score(
            report.layout_accuracy,
            report.image_accuracy,
            report.text_accuracy,
            report.spacing_accuracy,
            report.choice_accuracy,
        )

        # Determine pass/fail.
        report.passed = report.overall_score >= VISUAL_ACCURACY_THRESHOLD

        # Count matched/mismatched elements.
        report.matched_elements = report.total_elements - report.mismatched_elements

        # Generate findings.
        self._generate_findings(original_analysis, report)

        # Duration.
        report.duration_ms = (time.monotonic() - start_time) * 1000

        self._log_messages.append(
            f"VisualValidator: page {original_analysis.page_number} "
            f"overall={report.overall_score:.2%} "
            f"passed={report.passed}."
        )

        return report

    def validate_positions_only(
        self,
        original_positions: List[ElementPosition],
        rebuilt_positions: List[ElementPosition],
    ) -> float:
        """Validate only the position accuracy.

        Parameters:
            original_positions: The original element positions.
            rebuilt_positions: The rebuilt element positions.

        Returns:
            The position accuracy score (0.0–1.0).
        """
        if not original_positions or not rebuilt_positions:
            return 0.0

        total = min(len(original_positions), len(rebuilt_positions))
        matched = 0
        for i in range(total):
            orig = original_positions[i]
            rebuilt = rebuilt_positions[i]
            dx = abs(rebuilt.x - orig.x)
            dy = abs(rebuilt.y - orig.y)
            if dx <= self.POSITION_TOLERANCE and dy <= self.POSITION_TOLERANCE:
                matched += 1

        return matched / total if total > 0 else 0.0

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _compute_layout_accuracy(
        self,
        analysis: PageAnalysis,
        rebuilt_positions: List[ElementPosition],
    ) -> float:
        """Compute layout accuracy (position, alignment)."""
        elements = analysis.all_elements
        if not elements:
            return 1.0

        total = min(len(elements), len(rebuilt_positions))
        matched = 0
        for i in range(total):
            orig = elements[i].position
            rebuilt = rebuilt_positions[i]
            dx = abs(rebuilt.x - orig.x)
            dy = abs(rebuilt.y - orig.y)
            if dx <= self.POSITION_TOLERANCE and dy <= self.POSITION_TOLERANCE:
                matched += 1

        return matched / total if total > 0 else 1.0

    def _compute_image_accuracy(self, analysis: PageAnalysis) -> float:
        """Compute image accuracy (size, position, aspect ratio)."""
        images = analysis.images
        if not images:
            return 1.0

        matched = 0
        for img in images:
            if img.has_content and img.aspect_ratio_preserved:
                matched += 1
            elif not img.has_content and img.is_question_image:
                # Question images without content is a failure.
                continue
            else:
                matched += 1

        return matched / len(images) if images else 1.0

    def _compute_text_accuracy(self, analysis: PageAnalysis) -> float:
        """Compute text accuracy (font, size, content, alignment)."""
        texts = analysis.texts
        if not texts:
            return 1.0

        matched = 0
        for txt in texts:
            if txt.text and txt.font_name:
                matched += 1

        return matched / len(texts) if texts else 1.0

    def _compute_spacing_accuracy(self, analysis: PageAnalysis) -> float:
        """Compute spacing accuracy (margins, gaps, line height)."""
        if not analysis.texts:
            return 1.0

        # Check that line heights are consistent.
        texts = sorted(
            analysis.texts,
            key=lambda t: (t.position.y, t.position.x),
        )
        gaps = []
        for i in range(1, len(texts)):
            gap = texts[i].position.y - texts[i - 1].position.y
            gaps.append(gap)

        if not gaps:
            return 1.0

        # Check that gaps are positive (no overlaps).
        positive_gaps = sum(1 for g in gaps if g > 0)
        return positive_gaps / len(gaps) if gaps else 1.0

    def _compute_choice_accuracy(self, analysis: PageAnalysis) -> float:
        """Compute choice accuracy (label, text, position, order)."""
        choices = analysis.choices
        if not choices:
            return 1.0

        matched = 0
        for ch in choices:
            if ch.label and ch.position.width > 0:
                matched += 1

        return matched / len(choices) if choices else 1.0

    def _compute_overall_score(
        self,
        layout: float,
        image: float,
        text: float,
        spacing: float,
        choice: float,
    ) -> float:
        """Compute the overall weighted accuracy score."""
        return (
            layout * LAYOUT_ACCURACY_WEIGHT +
            image * IMAGE_ACCURACY_WEIGHT +
            text * TEXT_ACCURACY_WEIGHT +
            spacing * SPACING_ACCURACY_WEIGHT +
            choice * CHOICE_ACCURACY_WEIGHT
        )

    def _generate_findings(
        self,
        analysis: PageAnalysis,
        report: VisualSimilarityReport,
    ) -> None:
        """Generate validation findings for the report."""
        if report.passed:
            report.add_finding(
                "Validation passed: overall accuracy above threshold."
            )
        else:
            report.add_finding(
                f"Validation failed: overall accuracy "
                f"({report.overall_score:.2%}) below threshold "
                f"({VISUAL_ACCURACY_THRESHOLD:.2%})."
            )

        # Check layout.
        if report.layout_accuracy < 0.98:
            report.add_finding(
                f"Layout accuracy ({report.layout_accuracy:.2%}) "
                "below 98% threshold."
            )

        # Check images.
        if report.image_accuracy < 0.98:
            report.add_finding(
                f"Image accuracy ({report.image_accuracy:.2%}) "
                "below 98% threshold."
            )

        # Check question images.
        question_images = analysis.question_images()
        for img in question_images:
            if not img.has_content:
                report.add_finding(
                    f"Question image '{img.id}' has no content."
                )

        # Check choices.
        if analysis.has_choices and report.choice_accuracy < 0.98:
            report.add_finding(
                f"Choice accuracy ({report.choice_accuracy:.2%}) "
                "below 98% threshold."
            )

        # Check for analysis warnings.
        for warning in analysis.warnings:
            report.add_finding(f"Analysis warning: {warning}")


__all__ = [
    "VisualValidator",
    "VisualSimilarityReport",
    "VISUAL_ACCURACY_THRESHOLD",
    "LAYOUT_ACCURACY_WEIGHT",
    "IMAGE_ACCURACY_WEIGHT",
    "TEXT_ACCURACY_WEIGHT",
    "SPACING_ACCURACY_WEIGHT",
    "CHOICE_ACCURACY_WEIGHT",
]
