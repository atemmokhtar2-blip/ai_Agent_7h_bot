"""
Page Analyzer — performs a complete analysis of a single PDF page.

The :class:`PageAnalyzer` is a stateless helper that the
:class:`VisualPageReconstructionEngine` calls during the *analysis*
phase.  It reads the raw PDF page and produces a :class:`PageAnalysis`
that captures every element with its exact position, size, rotation,
and visual layer.

The analyzer is responsible for:
1. Detecting page dimensions (width, height, margins, orientation).
2. Detecting the number of columns.
3. Detecting the writing direction (LTR / RTL).
4. Extracting all text elements with font metadata.
5. Extracting all images (delegating to :class:`ImageExtractor`).
6. Detecting choices (أ، ب، ج، د / A, B, C, D).
7. Detecting tables.
8. Detecting equations.
9. Detecting separator lines.
10. Assigning visual layers to every element.
11. Building the ordered layer list.

Acceptance rules
----------------
* Every element must have X, Y, Width, Height, Rotation, Layer.
* No element may be omitted or merged.
* Images must come from the :class:`ImageExtractor` (embedded stream).
* Choices must preserve their original position, order, spacing, and
  shape.
"""
from __future__ import annotations
import re
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple
from .page_analysis import (
    PageAnalysis,
    PageDimensions,
    PageElement,
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

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class PageAnalyzer:
    """Analyses a single PDF page and produces a :class:`PageAnalysis`.

    The analyzer is stateless.  Call :meth:`analyse` with a PDF page
    object and page number to get the full analysis.
    """

    # Arabic choice labels
    ARABIC_CHOICES: List[str] = [
        "أ", "ب", "ج", "د", "هـ", "و", "ز", "ح",
    ]
    # English choice labels
    ENGLISH_CHOICES: List[str] = [
        "A", "B", "C", "D", "E", "F", "G", "H",
    ]
    # Combined choice label pattern
    CHOICE_PATTERN = re.compile(
        r"^[أ-يA-Ha-h]\s*[\.\)\:]?\s*$|^[أ-يA-Ha-h]\)\s*$|"
        r"^[\(（][أ-يA-Ha-h][\)）]?\s*$",
    )

    def __init__(self) -> None:
        self._image_extractor = ImageExtractor()
        self._log_messages: List[str] = []

    @property
    def log_messages(self) -> List[str]:
        return list(self._log_messages)

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def analyse(
        self, pdf_page: Any, page_number: int,
        source_path: str = "",
    ) -> PageAnalysis:
        """Analyse a single PDF page.

        Parameters:
            pdf_page: A ``pdfplumber`` page object.
            page_number: The 1-based page number.
            source_path: The path to the source PDF file.

        Returns:
            A :class:`PageAnalysis` with all elements detected.
        """
        analysis = PageAnalysis(
            page_number=page_number,
            source_pdf_path=source_path,
        )

        # Step 1: page dimensions.
        analysis.dimensions = self._detect_dimensions(pdf_page)
        self._log_messages.append(
            f"PageAnalyzer: page {page_number} dimensions: "
            f"{analysis.dimensions.width}x{analysis.dimensions.height} "
            f"({analysis.dimensions.orientation})."
        )

        # Step 2: writing direction.
        analysis.writing_direction = self._detect_writing_direction(pdf_page)
        self._log_messages.append(
            f"PageAnalyzer: page {page_number} direction: "
            f"{analysis.writing_direction}."
        )

        # Step 3: column count.
        analysis.column_count = self._detect_column_count(pdf_page)
        self._log_messages.append(
            f"PageAnalyzer: page {page_number} columns: "
            f"{analysis.column_count}."
        )

        # Step 4: text elements.
        analysis.texts = self._extract_texts(pdf_page, analysis.dimensions)
        self._log_messages.append(
            f"PageAnalyzer: page {page_number} found "
            f"{len(analysis.texts)} text element(s)."
        )

        # Step 5: image elements.
        analysis.images = self._image_extractor.extract_from_page(
            pdf_page, page_number,
            analysis.dimensions.width, analysis.dimensions.height,
        )
        self._log_messages.append(
            f"PageAnalyzer: page {page_number} found "
            f"{len(analysis.images)} image(s)."
        )

        # Step 6: choice detection.
        analysis.choices = self._detect_choices(pdf_page, analysis.dimensions)
        self._log_messages.append(
            f"PageAnalyzer: page {page_number} found "
            f"{len(analysis.choices)} choice(s)."
        )

        # Step 7: table detection.
        analysis.tables = self._detect_tables(pdf_page, analysis.dimensions)
        self._log_messages.append(
            f"PageAnalyzer: page {page_number} found "
            f"{len(analysis.tables)} table(s)."
        )

        # Step 8: equation detection.
        analysis.equations = self._detect_equations(pdf_page, analysis.dimensions)
        self._log_messages.append(
            f"PageAnalyzer: page {page_number} found "
            f"{len(analysis.equations)} equation(s)."
        )

        # Step 9: separator detection.
        analysis.separators = self._detect_separators(pdf_page, analysis.dimensions)
        self._log_messages.append(
            f"PageAnalyzer: page {page_number} found "
            f"{len(analysis.separators)} separator(s)."
        )

        # Step 10: build visual layers.
        analysis.layers = self._build_layers(analysis)
        self._log_messages.append(
            f"PageAnalyzer: page {page_number} built "
            f"{len(analysis.layers)} layer(s)."
        )

        # Step 11: compute element count.
        analysis.element_count = (
            len(analysis.images) + len(analysis.texts) +
            len(analysis.choices) + len(analysis.tables) +
            len(analysis.equations) + len(analysis.separators) +
            len(analysis.shapes)
        )

        # Step 12: validation warnings.
        self._validate_analysis(analysis)

        return analysis

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _detect_dimensions(self, pdf_page: Any) -> PageDimensions:
        """Detect page dimensions from the pdfplumber page object."""
        if pdf_page is None:
            return PageDimensions()
        width = float(pdf_page.width)
        height = float(pdf_page.height)
        orientation = "portrait" if height >= width else "landscape"

        # Detect margins from text bounding boxes.
        margin_left = 0.0
        margin_right = 0.0
        margin_top = 0.0
        margin_bottom = 0.0

        words = getattr(pdf_page, "words", []) or []
        if words:
            left_edges = [float(w["x0"]) for w in words]
            right_edges = [float(w["x1"]) for w in words]
            top_edges = [float(w["top"]) for w in words]
            bottom_edges = [float(w["bottom"]) for w in words]
            if left_edges:
                margin_left = min(left_edges) if left_edges else 0.0
            if right_edges:
                margin_right = width - max(right_edges) if right_edges else 0.0
            if top_edges:
                margin_top = min(top_edges) if top_edges else 0.0
            if bottom_edges:
                margin_bottom = height - max(bottom_edges) if bottom_edges else 0.0

        return PageDimensions(
            width=width,
            height=height,
            margin_left=margin_left,
            margin_right=margin_right,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
            orientation=orientation,
        )

    def _detect_writing_direction(self, pdf_page: Any) -> str:
        """Detect the primary writing direction of the page.

        If the page contains significant Arabic text, it is considered
        RTL.
        """
        if pdf_page is None:
            return "ltr"
        words = getattr(pdf_page, "words", []) or []
        arabic_count = 0
        latin_count = 0
        arabic_pattern = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")
        for word in words:
            text = word.get("text", "")
            if arabic_pattern.search(text):
                arabic_count += 1
            elif text.strip().isalpha():
                latin_count += 1
        return "rtl" if arabic_count > latin_count else "ltr"

    def _detect_column_count(self, pdf_page: Any) -> int:
        """Detect the number of columns on the page.

        Uses the distribution of text x-positions to determine whether
        the page has a single column or multiple columns.
        """
        if pdf_page is None:
            return 1
        words = getattr(pdf_page, "words", []) or []
        if len(words) < 3:
            return 1

        x_positions = sorted(float(w["x0"]) for w in words)
        # Find gaps larger than 20% of page width.
        page_width = float(pdf_page.width)
        threshold = page_width * 0.2
        gaps = 0
        for i in range(1, len(x_positions)):
            if x_positions[i] - x_positions[i - 1] > threshold:
                gaps += 1

        # Heuristic: if there are many gaps, assume multiple columns.
        if gaps >= len(x_positions) * 0.15:
            return 2
        return 1

    def _extract_texts(self, pdf_page: Any, dims: PageDimensions) -> List[PageText]:
        """Extract all text elements from the page."""
        texts: List[PageText] = []
        if pdf_page is None:
            return texts

        chars = getattr(pdf_page, "chars", []) or []
        # Group characters into text runs by proximity.
        runs = self._group_chars_into_runs(chars)
        for idx, run in enumerate(runs):
            text_id = f"txt_p{self._page_number_for_page(pdf_page)}_{idx}"
            position = ElementPosition(
                x=float(run["x0"]),
                y=float(run["top"]),
                width=float(run.get("width", run.get("x1", run["x0"]) - run["x0"])),
                height=float(run.get("height", run.get("bottom", run["top"]) - run["top"])),
                rotation=float(run.get("rot", 0)),
                layer=VISUAL_LAYER_TEXT,
            )
            is_heading = self._is_heading(run)
            text_obj = PageText(
                id=text_id,
                position=position,
                text=run.get("text", ""),
                font_name=run.get("fontname", ""),
                font_size=float(run.get("size", 0)),
                is_bold=run.get("is_bold", False),
                is_italic=run.get("is_italic", False),
                text_alignment=run.get("alignment", "left"),
                direction="rtl" if run.get("direction") == "rtl" else "ltr",
                is_heading=is_heading,
                heading_level=run.get("heading_level", 0) if is_heading else 0,
            )
            texts.append(text_obj)
        return texts

    def _group_chars_into_runs(self, chars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group individual characters into text runs.

        Characters that are close together (horizontally within 2 points
        and vertically within 1 point) are merged into a single text
        run.
        """
        if not chars:
            return []

        # Sort characters by position (top, then x0).
        sorted_chars = sorted(
            chars,
            key=lambda c: (float(c.get("top", 0)), float(c.get("x0", 0))),
        )

        runs: List[Dict[str, Any]] = []
        current_run: Dict[str, Any] = {}

        for char in sorted_chars:
            top = float(char.get("top", 0))
            bottom = float(char.get("bottom", 0))
            x0 = float(char.get("x0", 0))
            x1 = float(char.get("x1", 0))
            size = float(char.get("size", 0))
            fontname = char.get("fontname", "")
            rot = float(char.get("rot", 0))

            if not current_run:
                current_run = {
                    "x0": x0,
                    "x1": x1,
                    "top": top,
                    "bottom": bottom,
                    "text": char.get("text", ""),
                    "fontname": fontname,
                    "size": size,
                    "rot": rot,
                    "chars": [char],
                }
                continue

            # Check if this character belongs to the current run.
            run_bottom = current_run["bottom"]
            run_height = run_bottom - current_run["top"]
            vertical_tolerance = max(1.0, run_height * 0.3)
            horizontal_tolerance = size * 1.5 if size > 0 else 5.0

            if (
                abs(top - current_run["top"]) <= vertical_tolerance and
                abs(x0 - current_run["x1"]) <= horizontal_tolerance and
                fontname == current_run.get("fontname", "")
            ):
                # Merge into current run.
                current_run["text"] += char.get("text", "")
                current_run["x1"] = x1
                current_run["bottom"] = max(run_bottom, bottom)
                current_run["chars"].append(char)
            else:
                # Finalise current run and start a new one.
                runs.append(self._finalise_run(current_run))
                current_run = {
                    "x0": x0,
                    "x1": x1,
                    "top": top,
                    "bottom": bottom,
                    "text": char.get("text", ""),
                    "fontname": fontname,
                    "size": size,
                    "rot": rot,
                    "chars": [char],
                }

        if current_run:
            runs.append(self._finalise_run(current_run))

        return runs

    @staticmethod
    def _finalise_run(run: Dict[str, Any]) -> Dict[str, Any]:
        """Finalise a character run into a clean text-run dict."""
        run["width"] = run["x1"] - run["x0"]
        run["height"] = run["bottom"] - run["top"]
        run["alignment"] = "center" if run.get("rot", 0) != 0 else "left"
        # Detect bold/italic from font name.
        fontname = run.get("fontname", "").lower()
        run["is_bold"] = "bold" in fontname or "black" in fontname
        run["is_italic"] = "italic" in fontname or "oblique" in fontname
        return run

    def _page_number_for_page(self, pdf_page: Any) -> int:
        """Get the page number from a pdfplumber page object."""
        # pdfplumber stores page index as 0-based; we need 1-based.
        return pdf_page.page_number + 1 if hasattr(pdf_page, "page_number") else 1

    def _is_heading(self, run: Dict[str, Any]) -> bool:
        """Determine whether a text run is a heading.

        Headings are detected by font size (significantly larger than
        the median) and bold weight.
        """
        font_size = run.get("size", 0)
        is_bold = run.get("is_bold", False)
        if font_size >= 14 and is_bold:
            return True
        if font_size >= 18:
            return True
        return False

    def _detect_choices(self, pdf_page: Any, dims: PageDimensions) -> List[PageChoice]:
        """Detect multiple-choice options on the page.

        Choices are detected by matching text patterns like
        ``أ.``, ``ب)``, ``A.``, ``B)``, etc.
        """
        choices: List[PageChoice] = []
        if pdf_page is None:
            return choices

        words = getattr(pdf_page, "words", []) or []
        for idx, word in enumerate(words):
            text = word.get("text", "").strip()
            if not text:
                continue
            if self.CHOICE_PATTERN.match(text):
                label = text.strip(".):").strip()
                # Find the adjacent text that is the choice content.
                next_text = ""
                if idx + 1 < len(words):
                    next_word = words[idx + 1]
                    if abs(float(next_word.get("top", 0)) - float(word.get("top", 0))) < 5:
                        next_text = next_word.get("text", "").strip()

                choice_id = f"choice_p{self._page_number_for_page(pdf_page)}_{len(choices)}"
                position = ElementPosition(
                    x=float(word.get("x0", 0)),
                    y=float(word.get("top", 0)),
                    width=float(word.get("x1", 0)) - float(word.get("x0", 0)),
                    height=float(word.get("bottom", 0)) - float(word.get("top", 0)),
                    rotation=float(word.get("rot", 0)),
                    layer=VISUAL_LAYER_TEXT,
                )
                choices.append(PageChoice(
                    id=choice_id,
                    position=position,
                    label=label,
                    text=next_text,
                    metadata={
                        "page_number": self._page_number_for_page(pdf_page),
                        "index": idx,
                    },
                ))
        return choices

    def _detect_tables(self, pdf_page: Any, dims: PageDimensions) -> List[PageTable]:
        """Detect tables on the page using pdfplumber's table finder."""
        tables: List[PageTable] = []
        if pdf_page is None:
            return tables

        try:
            pdf_tables = pdf_page.find_tables()
        except Exception:
            return tables

        for idx, pdf_table in enumerate(pdf_tables):
            try:
                data = pdf_table.extract()
                if not data:
                    continue
                table_id = f"table_p{self._page_number_for_page(pdf_page)}_{idx}"
                bbox = pdf_table.bbox
                position = ElementPosition(
                    x=float(bbox[0]),
                    y=float(bbox[1]),
                    width=float(bbox[2]) - float(bbox[0]),
                    height=float(bbox[3]) - float(bbox[1]),
                    layer=VISUAL_LAYER_TEXT,
                )
                rows = len(data)
                columns = max(len(row) for row in data) if data else 0
                cells = [
                    [str(cell) if cell is not None else "" for cell in row]
                    for row in data
                ]
                tables.append(PageTable(
                    id=table_id,
                    position=position,
                    rows=rows,
                    columns=columns,
                    cells=cells,
                    has_borders=True,
                ))
            except Exception:
                continue
        return tables

    def _detect_equations(self, pdf_page: Any, dims: PageDimensions) -> List[PageEquation]:
        """Detect mathematical equations on the page.

        Equations are detected by looking for characters that are not
        in standard text fonts, or by pattern matching common
        mathematical symbols.
        """
        equations: List[PageEquation] = []
        if pdf_page is None:
            return equations

        # Simple pattern-based detection for now.
        # A more sophisticated approach would use font analysis.
        chars = getattr(pdf_page, "chars", []) or []
        math_fonts = {"msbm10", "msam10", "cmmi10", "cmex10", "cmbx10"}
        current_eq_chars: List[Dict[str, Any]] = []
        eq_idx = 0

        for char in chars:
            fontname = char.get("fontname", "").lower()
            is_math = any(mf in fontname for mf in math_fonts)
            text = char.get("text", "")
            math_symbols = set("∑∏∫√∂∞±≤≥≠≈∝∠⊂⊃∈∉")
            is_symbol = text in math_symbols

            if is_math or is_symbol:
                current_eq_chars.append(char)
            else:
                if len(current_eq_chars) >= 2:
                    eq = self._build_equation(current_eq_chars, eq_idx, pdf_page)
                    equations.append(eq)
                    eq_idx += 1
                current_eq_chars = []

        if len(current_eq_chars) >= 2:
            eq = self._build_equation(current_eq_chars, eq_idx, pdf_page)
            equations.append(eq)

        return equations

    def _build_equation(
        self, eq_chars: List[Dict[str, Any]], idx: int, pdf_page: Any,
    ) -> PageEquation:
        """Build a PageEquation from a list of equation characters."""
        page_num = self._page_number_for_page(pdf_page)
        eq_id = f"eq_p{page_num}_{idx}"
        x0 = min(float(c.get("x0", 0)) for c in eq_chars)
        x1 = max(float(c.get("x1", 0)) for c in eq_chars)
        top = min(float(c.get("top", 0)) for c in eq_chars)
        bottom = max(float(c.get("bottom", 0)) for c in eq_chars)
        text = "".join(c.get("text", "") for c in eq_chars)
        position = ElementPosition(
            x=x0, y=top,
            width=x1 - x0, height=bottom - top,
            layer=VISUAL_LAYER_TEXT,
        )
        return PageEquation(
            id=eq_id,
            position=position,
            rendered_text=text,
        )

    def _detect_separators(self, pdf_page: Any, dims: PageDimensions) -> List[PageSeparator]:
        """Detect horizontal and vertical separator lines on the page."""
        separators: List[PageSeparator] = []
        if pdf_page is None:
            return separators

        lines = getattr(pdf_page, "lines", []) or []
        rect_edges = getattr(pdf_page, "rect_edges", []) or []

        # Horizontal lines.
        for idx, line in enumerate(lines):
            x0 = float(line.get("x0", 0))
            x1 = float(line.get("x1", 0))
            top = float(line.get("top", 0))
            bottom = float(line.get("bottom", 0))
            width = x1 - x0
            height = bottom - top
            thickness = max(height, 0.5)
            sep_id = f"sep_p{self._page_number_for_page(pdf_page)}_{idx}"
            separators.append(PageSeparator(
                id=sep_id,
                position=ElementPosition(
                    x=x0, y=top, width=width, height=height,
                    layer=VISUAL_LAYER_SHAPE,
                ),
                orientation="horizontal",
                thickness=thickness,
                color=line.get("non_stroking_color", "#000000"),
            ))

        return separators

    def _build_layers(self, analysis: PageAnalysis) -> List[VisualLayer]:
        """Build the ordered list of visual layers from the analysis."""
        background_layer = VisualLayer(
            name=VISUAL_LAYER_BACKGROUND, z_index=0,
        )
        image_layer = VisualLayer(name=VISUAL_LAYER_IMAGE, z_index=10)
        shape_layer = VisualLayer(name=VISUAL_LAYER_SHAPE, z_index=20)
        text_layer = VisualLayer(name=VISUAL_LAYER_TEXT, z_index=30)
        overlay_layer = VisualLayer(name=VISUAL_LAYER_OVERLAY, z_index=40)

        # Assign elements to layers.
        for img in analysis.images:
            image_layer.add_element(PageElement(
                id=img.id,
                element_type=ELEMENT_TYPE_IMAGE,
                position=img.position,
                metadata=img.metadata,
            ))
        for sep in analysis.separators:
            shape_layer.add_element(PageElement(
                id=sep.id,
                element_type=ELEMENT_TYPE_SEPARATOR,
                position=sep.position,
                metadata=sep.metadata,
            ))
        for txt in analysis.texts:
            text_layer.add_element(PageElement(
                id=txt.id,
                element_type=ELEMENT_TYPE_TEXT,
                position=txt.position,
                metadata=txt.metadata,
            ))
        for ch in analysis.choices:
            text_layer.add_element(PageElement(
                id=ch.id,
                element_type=ELEMENT_TYPE_CHOICE,
                position=ch.position,
                metadata=ch.metadata,
            ))

        layers = [background_layer, image_layer, shape_layer, text_layer, overlay_layer]
        return layers

    def _validate_analysis(self, analysis: PageAnalysis) -> None:
        """Validate the analysis and add warnings if needed."""
        # Check for missing images.
        for img in analysis.images:
            if not img.has_content:
                analysis.add_warning(
                    f"Image '{img.id}' has no extracted content.",
                )
            if img.is_question_image and not img.has_content:
                analysis.add_warning(
                    f"Question image '{img.id}' has no content — "
                    "this violates acceptance rules.",
                )

        # Check for missing choices.
        if analysis.has_choices:
            choice_labels = {ch.label for ch in analysis.choices}
            if len(choice_labels) < 2:
                analysis.add_warning(
                    "Fewer than 2 choice labels detected.",
                )

        # Check for element overlap.
        elements = analysis.all_elements
        for i in range(len(elements)):
            for j in range(i + 1, len(elements)):
                pi = elements[i].position
                pj = elements[j].position
                if self._overlaps(pi, pj):
                    analysis.add_warning(
                        f"Elements '{elements[i].id}' and "
                        f"'{elements[j].id}' overlap.",
                    )

    @staticmethod
    def _overlaps(a: ElementPosition, b: ElementPosition) -> bool:
        """Check whether two element positions overlap."""
        a_right = a.x + a.width
        b_right = b.x + b.width
        a_bottom = a.y + a.height
        b_bottom = b.y + b.height
        return not (
            a_right <= b.x or b_right <= a.x or
            a_bottom <= b.y or b_bottom <= a.y
        )


__all__ = ["PageAnalyzer"]
