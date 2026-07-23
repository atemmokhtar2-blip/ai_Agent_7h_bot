"""
Visual Page Reconstruction Engine package (Specification 009).
This package contains the PDFX AI Visual Page Reconstruction Engine —
the engine that performs pixel-accurate reconstruction of PDF pages.
It is designed to reproduce PDF pages with near-100% visual fidelity,
preserving every element in its original position, size, rotation, and
layer.

The engine follows the core principle: **"The original is the reference."**
No re-design, no visual improvement, no layout changes.

Public surface
--------------
* :class:`VisualPageReconstructionEngine` — the engine itself.
* :class:`PageAnalysis` and all of its sub-dataclasses
  (:class:`PageElement`, :class:`ElementPosition`,
  :class:`VisualLayer`, :class:`PageImage`, :class:`PageText`,
  :class:`PageChoice`, :class:`PageTable`, :class:`PageEquation`,
  :class:`PageSeparator`).
* :class:`VisualSimilarityReport` — the validation report.
* :class:`ImageExtractor` — the image extraction helper.
* :class:`PageAnalyzer` — the page analysis helper.
* :class:`LayoutRebuilder` — the layout reconstruction helper.
* :class:`ChoiceDetector` — the choice detection helper.
* :class:`CoordinateMapper` — the coordinate mapping helper.
* :class:`VisualValidator` — the visual similarity validator.
* Visual-layer and element-type constants.
"""
from __future__ import annotations
from .page_reconstruction_engine import VisualPageReconstructionEngine
from .page_analysis import (
    PageAnalysis,
    PageElement,
    ElementPosition,
    VisualLayer,
    PageImage,
    PageText,
    PageChoice,
    PageTable,
    PageEquation,
    PageSeparator,
    PageDimensions,
    VISUAL_LAYER_BACKGROUND,
    VISUAL_LAYER_IMAGE,
    VISUAL_LAYER_SHAPE,
    VISUAL_LAYER_TEXT,
    VISUAL_LAYER_OVERLAY,
    ALL_VISUAL_LAYERS,
    ELEMENT_TYPE_IMAGE,
    ELEMENT_TYPE_TEXT,
    ELEMENT_TYPE_CHOICE,
    ELEMENT_TYPE_TABLE,
    ELEMENT_TYPE_EQUATION,
    ELEMENT_TYPE_SEPARATOR,
    ELEMENT_TYPE_SHAPE,
    ALL_ELEMENT_TYPES,
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
    LAYOUT_ACCURACY_WEIGHT,
    IMAGE_ACCURACY_WEIGHT,
    TEXT_ACCURACY_WEIGHT,
    SPACING_ACCURACY_WEIGHT,
    CHOICE_ACCURACY_WEIGHT,
)
__all__ = [
    # Engine
    "VisualPageReconstructionEngine",
    # Data model
    "PageAnalysis",
    "PageElement",
    "ElementPosition",
    "VisualLayer",
    "PageImage",
    "PageText",
    "PageChoice",
    "PageTable",
    "PageEquation",
    "PageSeparator",
    "PageDimensions",
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
    # Helpers
    "ImageExtractor",
    "PageAnalyzer",
    "LayoutRebuilder",
    "ChoiceDetector",
    "CoordinateMapper",
    "VisualValidator",
    "VisualSimilarityReport",
    # Validation weights
    "VISUAL_ACCURACY_THRESHOLD",
    "LAYOUT_ACCURACY_WEIGHT",
    "IMAGE_ACCURACY_WEIGHT",
    "TEXT_ACCURACY_WEIGHT",
    "SPACING_ACCURACY_WEIGHT",
    "CHOICE_ACCURACY_WEIGHT",
]
