"""
Page Analysis — the data model for the Visual Page Reconstruction Engine
(Specification 009).

The :class:`PageAnalysis` is the **complete, authoritative** analysis of
a single PDF page.  It captures every element on the page with its
exact position, size, rotation, and visual layer.  This model is the
input to the layout rebuilder and the basis for the visual similarity
report.

Design principles
-----------------
* **Single responsibility per element.**  Each element has exactly one
  type and one visual layer.
* **Coordinate precision.**  Every element stores X, Y, Width, Height,
  Rotation, and Layer — matching the coordinate system defined in the
  specification.
* **Layer separation.**  Elements are grouped into visual layers so
  that the rebuilder can render them in the correct order without
  losing any element.
* **No re-design.**  The model preserves the original element data; it
  does not interpret, transform, or improve the layout.

Visual layers (rendering order, bottom to top)
----------------------------------------------
1. ``VISUAL_LAYER_BACKGROUND`` — the page background (colour, pattern).
2. ``VISUAL_LAYER_IMAGE`` — images extracted from the PDF.
3. ``VISUAL_LAYER_SHAPE`` — vector shapes (lines, rectangles, etc.).
4. ``VISUAL_LAYER_TEXT`` — all text content (headings, paragraphs, etc.).
5. ``VISUAL_LAYER_OVERLAY`` — overlays, watermarks, annotations.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Visual-layer constants
# ---------------------------------------------------------------------------
VISUAL_LAYER_BACKGROUND = "background"
VISUAL_LAYER_IMAGE = "image"
VISUAL_LAYER_SHAPE = "shape"
VISUAL_LAYER_TEXT = "text"
VISUAL_LAYER_OVERLAY = "overlay"

ALL_VISUAL_LAYERS = [
    VISUAL_LAYER_BACKGROUND,
    VISUAL_LAYER_IMAGE,
    VISUAL_LAYER_SHAPE,
    VISUAL_LAYER_TEXT,
    VISUAL_LAYER_OVERLAY,
]

# ---------------------------------------------------------------------------
# Element-type constants
# ---------------------------------------------------------------------------
ELEMENT_TYPE_IMAGE = "image"
ELEMENT_TYPE_TEXT = "text"
ELEMENT_TYPE_CHOICE = "choice"
ELEMENT_TYPE_TABLE = "table"
ELEMENT_TYPE_EQUATION = "equation"
ELEMENT_TYPE_SEPARATOR = "separator"
ELEMENT_TYPE_SHAPE = "shape"

ALL_ELEMENT_TYPES = [
    ELEMENT_TYPE_IMAGE,
    ELEMENT_TYPE_TEXT,
    ELEMENT_TYPE_CHOICE,
    ELEMENT_TYPE_TABLE,
    ELEMENT_TYPE_EQUATION,
    ELEMENT_TYPE_SEPARATOR,
    ELEMENT_TYPE_SHAPE,
]

# ---------------------------------------------------------------------------
# Element position
# ---------------------------------------------------------------------------
@dataclass
class ElementPosition:
    """The position and geometry of a single element on the page.
    Attributes:
        x: The X-coordinate of the element's top-left corner (points).
        y: The Y-coordinate of the element's top-left corner (points).
        width: The element's width (points).
        height: The element's height (points).
        rotation: The element's rotation in degrees (0–360).
        layer: The visual layer this element belongs to.
    """
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    rotation: float = 0.0
    layer: str = VISUAL_LAYER_TEXT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "layer": self.layer,
        }


# ---------------------------------------------------------------------------
# Visual layer descriptor
# ---------------------------------------------------------------------------
@dataclass
class VisualLayer:
    """A visual layer descriptor for rendering order.
    Attributes:
        name: The layer name (one of the ``VISUAL_LAYER_*`` constants).
        z_index: The rendering z-index (lower = rendered first).
        elements: The elements assigned to this layer.
    """
    name: str
    z_index: int = 0
    elements: List["PageElement"] = field(default_factory=list)

    def add_element(self, element: "PageElement") -> None:
        self.elements.append(element)

    @property
    def element_count(self) -> int:
        return len(self.elements)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "z_index": self.z_index,
            "element_count": self.element_count,
            "elements": [e.to_dict() for e in self.elements],
        }


# ---------------------------------------------------------------------------
# Page element
# ---------------------------------------------------------------------------
@dataclass
class PageElement:
    """A single element on a PDF page.
    Every element has a type, a position, and optional content data.
    Attributes:
        id: A unique identifier for this element within the page.
        element_type: The element type (one of the ``ELEMENT_TYPE_*``
            constants).
        position: The :class:`ElementPosition` of this element.
        content: The element's content (text string, image bytes,
            table data, etc.).
        metadata: Additional metadata about the element (font name,
            image format, table dimensions, etc.).
    """
    id: str = ""
    element_type: str = ELEMENT_TYPE_TEXT
    position: ElementPosition = field(default_factory=ElementPosition)
    content: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "element_type": self.element_type,
            "position": self.position.to_dict(),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Specialised element types
# ---------------------------------------------------------------------------
@dataclass
class PageImage:
    """An image element extracted from the PDF page.
    Attributes:
        id: A unique identifier for this image.
        position: The :class:`ElementPosition` of this image.
        image_bytes: The raw image bytes (extracted directly from the
            PDF, not a screenshot).
        image_format: The image format (``"png"``, ``"jpg"``, etc.).
        is_question_image: ``True`` when this image is part of a
            question (must not be deleted, replaced, or redrawn).
        aspect_ratio_preserved: ``True`` when the aspect ratio matches
            the original.
    """
    id: str = ""
    position: ElementPosition = field(
        default_factory=lambda: ElementPosition(layer=VISUAL_LAYER_IMAGE),
    )
    image_bytes: bytes = b""
    image_format: str = "png"
    is_question_image: bool = False
    aspect_ratio_preserved: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_content(self) -> bool:
        return len(self.image_bytes) > 0

    @property
    def is_embedded(self) -> bool:
        return self.metadata.get("extraction_method") == "embedded"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "image_format": self.image_format,
            "is_question_image": self.is_question_image,
            "aspect_ratio_preserved": self.aspect_ratio_preserved,
            "is_embedded": self.is_embedded,
            "has_content": self.has_content,
            "metadata": dict(self.metadata),
        }


@dataclass
class PageText:
    """A text element on the PDF page.
    Attributes:
        id: A unique identifier for this text.
        position: The :class:`ElementPosition` of this text.
        text: The actual text content.
        font_name: The font name used.
        font_size: The font size (points).
        is_bold: ``True`` when the text is bold.
        is_italic: ``True`` when the text is italic.
        text_alignment: The text alignment (``"left"``, ``"right"``,
            ``"center"``, ``"justify"``).
        direction: The text direction (``"ltr"`` or ``"rtl"``).
        is_heading: ``True`` when this text is a heading.
        heading_level: The heading level (1–6), or 0 for non-headings.
    """
    id: str = ""
    position: ElementPosition = field(default_factory=ElementPosition)
    text: str = ""
    font_name: str = ""
    font_size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False
    text_alignment: str = "left"
    direction: str = "ltr"
    is_heading: bool = False
    heading_level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "text": self.text,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "is_bold": self.is_bold,
            "is_italic": self.is_italic,
            "text_alignment": self.text_alignment,
            "direction": self.direction,
            "is_heading": self.is_heading,
            "heading_level": self.heading_level,
            "metadata": dict(self.metadata),
        }


@dataclass
class PageChoice:
    """A multiple-choice option on the PDF page.
    Attributes:
        id: A unique identifier for this choice.
        position: The :class:`ElementPosition` of this choice.
        label: The choice label (``"أ"``, ``"ب"``, ``"A"``, ``"B"``, etc.).
        text: The choice text content.
        is_correct: ``True`` when this choice is the correct answer
            (if detectable).
    """
    id: str = ""
    position: ElementPosition = field(default_factory=ElementPosition)
    label: str = ""
    text: str = ""
    is_correct: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "label": self.label,
            "text": self.text,
            "is_correct": self.is_correct,
            "metadata": dict(self.metadata),
        }


@dataclass
class PageTable:
    """A table element on the PDF page.
    Attributes:
        id: A unique identifier for this table.
        position: The :class:`ElementPosition` of this table.
        rows: The number of rows.
        columns: The number of columns.
        cells: A list of cell data (row-major order).
        has_borders: ``True`` when the table has visible borders.
    """
    id: str = ""
    position: ElementPosition = field(default_factory=ElementPosition)
    rows: int = 0
    columns: int = 0
    cells: List[List[str]] = field(default_factory=list)
    has_borders: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "rows": self.rows,
            "columns": self.columns,
            "cell_count": len(self.cells),
            "has_borders": self.has_borders,
            "metadata": dict(self.metadata),
        }


@dataclass
class PageEquation:
    """A mathematical equation on the PDF page.
    Attributes:
        id: A unique identifier for this equation.
        position: The :class:`ElementPosition` of this equation.
        latex: The LaTeX representation (if extractable).
        rendered_text: The plain-text rendering.
    """
    id: str = ""
    position: ElementPosition = field(default_factory=ElementPosition)
    latex: str = ""
    rendered_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "has_latex": bool(self.latex),
            "rendered_text": self.rendered_text,
            "metadata": dict(self.metadata),
        }


@dataclass
class PageSeparator:
    """A horizontal or vertical separator line on the PDF page.
    Attributes:
        id: A unique identifier for this separator.
        position: The :class:`ElementPosition` of this separator.
        orientation: ``"horizontal"`` or ``"vertical"``.
        thickness: The line thickness (points).
        color: The line colour as a hex string.
    """
    id: str = ""
    position: ElementPosition = field(default_factory=ElementPosition)
    orientation: str = "horizontal"
    thickness: float = 0.5
    color: str = "#000000"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "orientation": self.orientation,
            "thickness": self.thickness,
            "color": self.color,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Page dimensions
# ---------------------------------------------------------------------------
@dataclass
class PageDimensions:
    """The physical dimensions of a PDF page.
    Attributes:
        width: The page width (points).
        height: The page height (points).
        margin_left: The left margin (points).
        margin_right: The right margin (points).
        margin_top: The top margin (points).
        margin_bottom: The bottom margin (points).
        orientation: ``"portrait"`` or ``"landscape"``.
    """
    width: float = 0.0
    height: float = 0.0
    margin_left: float = 0.0
    margin_right: float = 0.0
    margin_top: float = 0.0
    margin_bottom: float = 0.0
    orientation: str = "portrait"

    @property
    def content_width(self) -> float:
        """The usable content width (page width minus margins)."""
        return self.width - self.margin_left - self.margin_right

    @property
    def content_height(self) -> float:
        """The usable content height (page height minus margins)."""
        return self.height - self.margin_top - self.margin_bottom

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "margin_left": self.margin_left,
            "margin_right": self.margin_right,
            "margin_top": self.margin_top,
            "margin_bottom": self.margin_bottom,
            "orientation": self.orientation,
            "content_width": self.content_width,
            "content_height": self.content_height,
        }


# ---------------------------------------------------------------------------
# Full page analysis
# ---------------------------------------------------------------------------
@dataclass
class PageAnalysis:
    """The complete analysis of a single PDF page.
    This is the **only** object the Visual Page Reconstruction Engine
    produces during the analysis phase.  It contains every element on
    the page, grouped by visual layer, together with the page
    dimensions and layout information.
    Attributes:
        page_number: The 1-based page number.
        dimensions: The :class:`PageDimensions` of the page.
        images: The list of :class:`PageImage` objects.
        texts: The list of :class:`PageText` objects.
        choices: The list of :class:`PageChoice` objects.
        tables: The list of :class:`PageTable` objects.
        equations: The list of :class:`PageEquation` objects.
        separators: The list of :class:`PageSeparator` objects.
        shapes: The list of generic :class:`PageElement` objects with
            type ``"shape"``.
        layers: The ordered list of :class:`VisualLayer` objects.
        element_count: The total number of elements detected.
        column_count: The detected number of columns (1, 2, 3, etc.).
        writing_direction: The primary writing direction
            (``"ltr"`` or ``"rtl"``).
        source_pdf_path: The path to the source PDF file.
        notes: General analysis notes.
        warnings: Warnings produced during analysis.
    """
    page_number: int = 1
    dimensions: PageDimensions = field(default_factory=PageDimensions)
    images: List[PageImage] = field(default_factory=list)
    texts: List[PageText] = field(default_factory=list)
    choices: List[PageChoice] = field(default_factory=list)
    tables: List[PageTable] = field(default_factory=list)
    equations: List[PageEquation] = field(default_factory=list)
    separators: List[PageSeparator] = field(default_factory=list)
    shapes: List[PageElement] = field(default_factory=list)
    layers: List[VisualLayer] = field(default_factory=list)
    element_count: int = 0
    column_count: int = 1
    writing_direction: str = "ltr"
    source_pdf_path: str = ""
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # -- convenience -------------------------------------------------------
    @property
    def image_count(self) -> int:
        return len(self.images)

    @property
    def text_count(self) -> int:
        return len(self.texts)

    @property
    def choice_count(self) -> int:
        return len(self.choices)

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def equation_count(self) -> int:
        return len(self.equations)

    @property
    def separator_count(self) -> int:
        return len(self.separators)

    @property
    def has_images(self) -> bool:
        return self.image_count > 0

    @property
    def has_choices(self) -> bool:
        return self.choice_count > 0

    @property
    def has_tables(self) -> bool:
        return self.table_count > 0

    @property
    def is_rtl(self) -> bool:
        return self.writing_direction == "rtl"

    @property
    def all_elements(self) -> List[PageElement]:
        """Return all elements across all types as a flat list."""
        elements: List[PageElement] = []
        for img in self.images:
            elements.append(PageElement(
                id=img.id,
                element_type=ELEMENT_TYPE_IMAGE,
                position=img.position,
                metadata=img.metadata,
            ))
        elements.extend(self.shapes)
        for txt in self.texts:
            elements.append(PageElement(
                id=txt.id,
                element_type=ELEMENT_TYPE_TEXT,
                position=txt.position,
                metadata=txt.metadata,
            ))
        for ch in self.choices:
            elements.append(PageElement(
                id=ch.id,
                element_type=ELEMENT_TYPE_CHOICE,
                position=ch.position,
                metadata=ch.metadata,
            ))
        for tbl in self.tables:
            elements.append(PageElement(
                id=tbl.id,
                element_type=ELEMENT_TYPE_TABLE,
                position=tbl.position,
                metadata=tbl.metadata,
            ))
        for eq in self.equations:
            elements.append(PageElement(
                id=eq.id,
                element_type=ELEMENT_TYPE_EQUATION,
                position=eq.position,
                metadata=eq.metadata,
            ))
        for sep in self.separators:
            elements.append(PageElement(
                id=sep.id,
                element_type=ELEMENT_TYPE_SEPARATOR,
                position=sep.position,
                metadata=sep.metadata,
            ))
        return elements

    def question_images(self) -> List[PageImage]:
        """Return only images that are part of questions."""
        return [img for img in self.images if img.is_question_image]

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "dimensions": self.dimensions.to_dict(),
            "element_count": self.element_count,
            "column_count": self.column_count,
            "writing_direction": self.writing_direction,
            "source_pdf_path": self.source_pdf_path,
            "image_count": self.image_count,
            "text_count": self.text_count,
            "choice_count": self.choice_count,
            "table_count": self.table_count,
            "equation_count": self.equation_count,
            "separator_count": self.separator_count,
            "layer_count": len(self.layers),
            "notes": list(self.notes),
            "warnings": list(self.warnings),
            "images": [img.to_dict() for img in self.images],
            "texts": [txt.to_dict() for txt in self.texts],
            "choices": [ch.to_dict() for ch in self.choices],
            "tables": [tbl.to_dict() for tbl in self.tables],
            "equations": [eq.to_dict() for eq in self.equations],
            "separators": [sep.to_dict() for sep in self.separators],
            "layers": [lyr.to_dict() for lyr in self.layers],
        }


__all__ = [
    # Visual-layer constants
    "VISUAL_LAYER_BACKGROUND",
    "VISUAL_LAYER_IMAGE",
    "VISUAL_LAYER_SHAPE",
    "VISUAL_LAYER_TEXT",
    "VISUAL_LAYER_OVERLAY",
    "ALL_VISUAL_LAYERS",
    # Element-type constants
    "ELEMENT_TYPE_IMAGE",
    "ELEMENT_TYPE_TEXT",
    "ELEMENT_TYPE_CHOICE",
    "ELEMENT_TYPE_TABLE",
    "ELEMENT_TYPE_EQUATION",
    "ELEMENT_TYPE_SEPARATOR",
    "ELEMENT_TYPE_SHAPE",
    "ALL_ELEMENT_TYPES",
    # Data model
    "ElementPosition",
    "VisualLayer",
    "PageElement",
    "PageImage",
    "PageText",
    "PageChoice",
    "PageTable",
    "PageEquation",
    "PageSeparator",
    "PageDimensions",
    "PageAnalysis",
]
