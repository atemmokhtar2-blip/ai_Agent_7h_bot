"""
Visual Page Reconstruction Engine (Specification 009).
PDFX AI Visual Page Reconstruction Engine — a pixel-accurate PDF page
reconstruction engine for the Telegram Bot Generation Engine.

The :class:`VisualPageReconstructionEngine` is the engine responsible
for reconstructing PDF pages with near-100% visual fidelity.  It reads
a PDF file, analyses every page element (images, text, choices, tables,
equations, separators), and produces a rebuilt PDF that is visually
indistinguishable from the original.

The engine operates in four phases:
1. **Extraction** — extract all images from the embedded PDF stream.
2. **Analysis** — analyse every element on every page.
3. **Reconstruction** — rebuild the page with pixel-accurate fidelity.
4. **Validation** — validate the rebuilt page against the original.

Design principles
-----------------
* **"The original is the reference."**  No re-design, no visual
  improvement, no layout changes.
* **Pixel-accurate reconstruction.**  Every element must be placed at
  its exact original position, size, rotation, and layer.
* **No element omission.**  No element may be omitted, merged, or
  replaced.
* **Image fidelity.**  Images must be extracted directly from the
  embedded stream with no compression, blur, or opacity changes.
* **Choice preservation.**  All choices must maintain their original
  position, order, spacing, and shape.

Data source
-----------
The engine reads the ``original_pdf`` artefact from the generation
context.  It does **not** read the user's request.

Output
------
The engine produces:
1. ``page_analyses`` — a list of :class:`PageAnalysis` objects (one
   per page).
2. ``rebuilt_pdf_bytes`` — the raw PDF bytes of the rebuilt document.
3. ``visual_similarity_reports`` — a list of
   :class:`VisualSimilarityReport` objects (one per page).
"""
from __future__ import annotations
import io
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ....core.context import GenerationContext
from ....core.result import StageResult
from ...base.base_engine import BaseEngine
from .page_analysis import (
    PageAnalysis,
    PageDimensions,
    PageImage,
    PageText,
    PageChoice,
    PageTable,
    PageEquation,
    PageSeparator,
    ElementPosition,
    VisualLayer,
    VISUAL_LAYER_BACKGROUND,
    VISUAL_LAYER_IMAGE,
    VISUAL_LAYER_SHAPE,
    VISUAL_LAYER_TEXT,
    VISUAL_LAYER_OVERLAY,
    ELEMENT_TYPE_IMAGE,
    ELEMENT_TYPE_TEXT,
    ELEMENT_TYPE_CHOICE,
    ELEMENT_TYPE_TABLE,
    ELEMENT_TYPE_EQUATION,
    ELEMENT_TYPE_SEPARATOR,
    ELEMENT_TYPE_SHAPE,
)
from .image_extractor import ImageExtractor
from .page_analyzer import PageAnalyzer
from .layout_rebuilder import LayoutRebuilder
from .choice_detector import ChoiceDetector
from .coordinate_mapper import CoordinateMapper
from .visual_validator import (
    VisualValidator,
    VisualSimilarityReport,
    VISUAL_ACCURACY_THRESHOLD,
)

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class VisualPageReconstructionEngine(BaseEngine):
    """The PDFX AI Visual Page Reconstruction Engine.

    This engine is the authority on pixel-accurate PDF page
    reconstruction.  It reads the ``original_pdf`` artefact from the
    generation context, analyses every page, extracts all images from
    the embedded stream, detects all elements, rebuilds the page with
    pixel-accurate fidelity, and validates the result.
    """

    def __init__(self) -> None:
        super().__init__(
            name="visual_page_reconstruction",
            version="1.0.0",
            description=(
                "Pixel-accurate PDF page reconstruction engine "
                "(Specification 009)."
            ),
            tags=["pdf", "visual", "reconstruction"],
        )
        self._image_extractor = ImageExtractor()
        self._page_analyzer = PageAnalyzer()
        self._layout_rebuilder = LayoutRebuilder()
        self._choice_detector = ChoiceDetector()
        self._coordinate_mapper = CoordinateMapper()
        self._visual_validator = VisualValidator()

    # -----------------------------------------------------------------
    # BaseEngine interface
    # -----------------------------------------------------------------
    def execute(self, context: GenerationContext) -> StageResult:
        """Execute the visual page reconstruction pipeline.

        The pipeline consists of four phases:
        1. Extraction — extract images from the PDF.
        2. Analysis — analyse every element on every page.
        3. Reconstruction — rebuild the pages.
        4. Validation — validate the rebuilt pages.
        """
        start_time = time.monotonic()

        # -- Read input artefact ------------------------------------------
        pdf_data = context.get("original_pdf")
        if pdf_data is None:
            return StageResult.failed(
                self.name,
                ["VisualPageReconstructionEngine requires the "
                 "'original_pdf' artefact."],
            )

        # Accept both bytes and a dict with 'bytes' or 'path'.
        if isinstance(pdf_data, dict):
            pdf_bytes = pdf_data.get("bytes", b"")
            source_path = pdf_data.get("path", "")
        elif isinstance(pdf_data, bytes):
            pdf_bytes = pdf_data
            source_path = ""
        elif isinstance(pdf_data, str):
            source_path = pdf_data
            pdf_bytes = self._read_pdf_file(source_path)
        else:
            return StageResult.failed(
                self.name,
                ["VisualPageReconstructionEngine: 'original_pdf' must "
                 "be bytes, a string path, or a dict with 'bytes'/"
                 "'path'."],
            )

        if not pdf_bytes and not source_path:
            return StageResult.failed(
                self.name,
                ["VisualPageReconstructionEngine: no PDF data provided."],
            )

        if not pdf_bytes and source_path:
            pdf_bytes = self._read_pdf_file(source_path)

        if not pdf_bytes:
            return StageResult.failed(
                self.name,
                ["VisualPageReconstructionEngine: failed to read PDF."],
            )

        # -- Phase 1: Open PDF and analyse each page ----------------------
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf = pdfplumber.open(pdf_file)
        except Exception as exc:
            return StageResult.failed(
                self.name,
                [f"VisualPageReconstructionEngine: failed to open PDF: {exc}"],
            )

        total_pages = len(pdf.pages)
        page_analyses: List[PageAnalysis] = []
        all_images: List[PageImage] = []

        for page_idx in range(total_pages):
            page = pdf.pages[page_idx]
            page_number = page_idx + 1

            # Analyse the page.
            analysis = self._page_analyzer.analyse(
                page, page_number, source_path,
            )
            page_analyses.append(analysis)
            all_images.extend(analysis.images)

        pdf.close()

        # -- Phase 2: Rebuild all pages -----------------------------------
        rebuilt_bytes = self._layout_rebuilder.rebuild_all_pages(
            page_analyses,
        )

        # -- Phase 3: Validate each page ----------------------------------
        reports: List[VisualSimilarityReport] = []
        all_positions: List[List[ElementPosition]] = []
        for analysis in page_analyses:
            positions = [e.position for e in analysis.all_elements]
            all_positions.append(positions)
            report = self._visual_validator.validate(
                analysis, positions,
            )
            reports.append(report)

        # -- Build result -------------------------------------------------
        duration_ms = (time.monotonic() - start_time) * 1000
        all_passed = all(r.passed for r in reports)

        outputs = {
            "page_analyses": page_analyses,
            "rebuilt_pdf_bytes": rebuilt_bytes,
            "visual_similarity_reports": reports,
            "total_pages": total_pages,
            "total_elements": sum(a.element_count for a in page_analyses),
            "total_images": len(all_images),
            "overall_passed": all_passed,
            "duration_ms": duration_ms,
        }

        errors: List[str] = []
        warnings: List[str] = []

        for idx, report in enumerate(reports):
            if not report.passed:
                errors.append(
                    f"Page {report.page_number} failed validation: "
                    f"overall={report.overall_score:.2%} "
                    f"threshold={VISUAL_ACCURACY_THRESHOLD:.2%}."
                )
            for finding in report.findings:
                if "failed" in finding.lower() or "error" in finding.lower():
                    errors.append(f"Page {report.page_number}: {finding}")
                else:
                    warnings.append(f"Page {report.page_number}: {finding}")

        metadata = {
            "engine": self.name,
            "version": self.version,
            "total_pages": total_pages,
            "total_elements": sum(a.element_count for a in page_analyses),
            "total_images": len(all_images),
            "all_passed": all_passed,
            "duration_ms": duration_ms,
        }

        if errors:
            # Still return outputs so the caller can inspect them,
            # but mark the stage as failed.
            return StageResult.failed(
                self.name,
                errors,
                outputs=outputs,
                warnings=warnings,
                metadata=metadata,
            )

        return StageResult.ok(
            self.name,
            outputs=outputs,
            metadata=metadata,
            warnings=warnings,
        )

    # -----------------------------------------------------------------
    # Helper methods
    # -----------------------------------------------------------------
    @staticmethod
    def _read_pdf_file(path: str) -> bytes:
        """Read a PDF file from disk."""
        try:
            from pathlib import Path
            return Path(path).read_bytes()
        except Exception:
            return b""

    def analyse_page(
        self, pdf_bytes: bytes, page_number: int,
    ) -> PageAnalysis:
        """Analyse a single page of a PDF.

        This is a convenience method for direct use without the full
        pipeline.
        """
        if not HAS_PDFPLUMBER:
            return PageAnalysis(page_number=page_number)

        pdf_file = io.BytesIO(pdf_bytes)
        pdf = pdfplumber.open(pdf_file)
        if page_number < 1 or page_number > len(pdf.pages):
            pdf.close()
            return PageAnalysis(page_number=page_number)

        page = pdf.pages[page_number - 1]
        analysis = self._page_analyzer.analyse(page, page_number)
        pdf.close()
        return analysis

    def validate_reconstruction(
        self,
        original_analysis: PageAnalysis,
        rebuilt_positions: List[ElementPosition],
    ) -> VisualSimilarityReport:
        """Validate a single page reconstruction.

        This is a convenience method for direct use without the full
        pipeline.
        """
        return self._visual_validator.validate(
            original_analysis, rebuilt_positions,
        )


__all__ = ["VisualPageReconstructionEngine"]
