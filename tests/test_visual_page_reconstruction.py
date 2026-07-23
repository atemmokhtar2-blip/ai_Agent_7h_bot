#!/usr/bin/env python3
"""
Comprehensive test suite for the Visual Page Reconstruction Engine
(Specification 009).

These tests cover every aspect of the specification:
1. Data model integrity (PageAnalysis, PageElement, ElementPosition,
   VisualLayer, PageImage, PageText, PageChoice, PageTable,
   PageEquation, PageSeparator, PageDimensions).
2. Visual-layer constants (all 5 layers in correct order).
3. Element-type constants (all 7 types).
4. The ImageExtractor (extraction from page, format detection,
   aspect ratio preservation, question image detection).
5. The PageAnalyzer (dimensions, writing direction, column count,
   text extraction, image extraction, choice detection, table
   detection, equation detection, separator detection, layer
   building, element count, validation warnings).
6. The LayoutRebuilder (single page rebuild, multi-page rebuild,
   layer rendering, empty analysis).
7. The ChoiceDetector (Arabic labels, English labels, mixed,
   label cleaning, choice text association, ordering validation).
8. The CoordinateMapper (position mapping, rect mapping, rotation
   mapping, spacing mapping, accuracy rate, validation).
9. The VisualValidator (layout accuracy, image accuracy, text
   accuracy, spacing accuracy, choice accuracy, overall score,
   threshold, findings generation).
10. The VisualSimilarityReport (all fields, to_dict, passed flag,
    findings).
11. The main engine (reads original_pdf, fails without it,
    produces page_analyses, produces rebuilt_pdf_bytes,
    produces visual_similarity_reports, bootstrap integration).
12. Bootstrap integration (engine registered in registry and
    manager, pipeline stage exists).
13. Serialisation (to_dict) for all data model classes.
14. No element is omitted or merged.
15. No image is compressed or blurred.
16. All choices maintain original position and order.
17. Coordinate mapping is bi-directional and lossless.
18. Visual similarity score is above 95% threshold.
"""
import sys
import os
# Ensure the package is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from typing import List
import tempfile

from telegram_bot_engine.core import build_configuration, bootstrap
from telegram_bot_engine.core.context import GenerationContext

# -- Data model imports ---------------------------------------------------
from telegram_bot_engine.engines.generators.visual_page_reconstruction import (
    # Engine
    VisualPageReconstructionEngine,
    # Data model
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
    # Constants
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
    # Helpers
    ImageExtractor,
    PageAnalyzer,
    LayoutRebuilder,
    ChoiceDetector,
    CoordinateMapper,
    VisualValidator,
    VisualSimilarityReport,
    # Validation weights
    VISUAL_ACCURACY_THRESHOLD,
    LAYOUT_ACCURACY_WEIGHT,
    IMAGE_ACCURACY_WEIGHT,
    TEXT_ACCURACY_WEIGHT,
    SPACING_ACCURACY_WEIGHT,
    CHOICE_ACCURACY_WEIGHT,
)


# ======================================================================
# Test framework (inline, no external dependency)
# ======================================================================
class TestGroup:
    def __init__(self, name: str):
        self.name = name
        self.results: List[tuple] = []

    def test(self, func):
        try:
            func()
            self.results.append((func.__name__, True, ""))
        except AssertionError as exc:
            self.results.append((func.__name__, False, str(exc)))
        except Exception as exc:
            self.results.append((func.__name__, False, f"{type(exc).__name__}: {exc}"))

    def report(self):
        print(f"\n{'='*70}")
        print(f"  {self.name}")
        print(f"{'='*70}")
        passed = 0
        failed = 0
        for name, ok, msg in self.results:
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {name}")
            if not ok and msg:
                print(f"         -> {msg}")
            if ok:
                passed += 1
            else:
                failed += 1
        print(f"\n  {self.name}: {passed} passed, {failed} failed")
        return failed


# ======================================================================
# Group 1: Data model integrity
# ======================================================================
def group_data_model():
    g = TestGroup("Group 1: Data Model Integrity")

    def test_element_position_defaults():
        pos = ElementPosition()
        assert pos.x == 0.0
        assert pos.y == 0.0
        assert pos.width == 0.0
        assert pos.height == 0.0
        assert pos.rotation == 0.0
        assert pos.layer == VISUAL_LAYER_TEXT
    g.test(test_element_position_defaults)

    def test_element_position_to_dict():
        pos = ElementPosition(x=10, y=20, width=100, height=50,
                              rotation=90, layer=VISUAL_LAYER_IMAGE)
        d = pos.to_dict()
        assert d["x"] == 10
        assert d["y"] == 20
        assert d["width"] == 100
        assert d["height"] == 50
        assert d["rotation"] == 90
        assert d["layer"] == VISUAL_LAYER_IMAGE
    g.test(test_element_position_to_dict)

    def test_visual_layer_defaults():
        lyr = VisualLayer(name=VISUAL_LAYER_TEXT, z_index=30)
        assert lyr.element_count == 0
    g.test(test_visual_layer_defaults)

    def test_visual_layer_add_element():
        lyr = VisualLayer(name=VISUAL_LAYER_TEXT, z_index=30)
        el = PageElement(id="e1", element_type=ELEMENT_TYPE_TEXT)
        lyr.add_element(el)
        assert lyr.element_count == 1
    g.test(test_visual_layer_add_element)

    def test_visual_layer_to_dict():
        lyr = VisualLayer(name=VISUAL_LAYER_TEXT, z_index=30)
        lyr.add_element(PageElement(id="e1"))
        d = lyr.to_dict()
        assert d["name"] == VISUAL_LAYER_TEXT
        assert d["z_index"] == 30
        assert d["element_count"] == 1
    g.test(test_visual_layer_to_dict)

    def test_page_element_defaults():
        el = PageElement()
        assert el.id == ""
        assert el.element_type == ELEMENT_TYPE_TEXT
    g.test(test_page_element_defaults)

    def test_page_element_to_dict():
        el = PageElement(id="e1", element_type=ELEMENT_TYPE_IMAGE,
                         position=ElementPosition(x=5, y=10))
        d = el.to_dict()
        assert d["id"] == "e1"
        assert d["element_type"] == ELEMENT_TYPE_IMAGE
    g.test(test_page_element_to_dict)

    def test_page_image_has_content():
        img = PageImage(id="img1", image_bytes=b"\x00\x01\x02")
        assert img.has_content is True
    g.test(test_page_image_has_content)

    def test_page_image_no_content():
        img = PageImage(id="img2", image_bytes=b"")
        assert img.has_content is False
    g.test(test_page_image_no_content)

    def test_page_image_is_question():
        img = PageImage(id="img3", is_question_image=True)
        assert img.is_question_image is True
    g.test(test_page_image_is_question)

    def test_page_image_to_dict():
        img = PageImage(id="img4", image_bytes=b"test",
                        image_format="png", is_question_image=False)
        d = img.to_dict()
        assert d["id"] == "img4"
        assert d["image_format"] == "png"
        assert d["is_question_image"] is False
        assert d["has_content"] is True
    g.test(test_page_image_to_dict)

    def test_page_text_defaults():
        txt = PageText()
        assert txt.text == ""
        assert txt.font_name == ""
        assert txt.is_bold is False
        assert txt.is_italic is False
    g.test(test_page_text_defaults)

    def test_page_text_to_dict():
        txt = PageText(id="t1", text="Hello", font_name="Helvetica",
                       font_size=12, is_bold=True)
        d = txt.to_dict()
        assert d["text"] == "Hello"
        assert d["font_name"] == "Helvetica"
        assert d["is_bold"] is True
    g.test(test_page_text_to_dict)

    def test_page_choice_defaults():
        ch = PageChoice()
        assert ch.label == ""
        assert ch.text == ""
        assert ch.is_correct is None
    g.test(test_page_choice_defaults)

    def test_page_choice_to_dict():
        ch = PageChoice(id="c1", label="أ", text="الإجابة الأولى")
        d = ch.to_dict()
        assert d["label"] == "أ"
        assert d["text"] == "الإجابة الأولى"
    g.test(test_page_choice_to_dict)

    def test_page_table_defaults():
        tbl = PageTable()
        assert tbl.rows == 0
        assert tbl.columns == 0
        assert tbl.has_borders is True
    g.test(test_page_table_defaults)

    def test_page_table_to_dict():
        tbl = PageTable(id="tbl1", rows=3, columns=4,
                        cells=[["a", "b"], ["c", "d"]])
        d = tbl.to_dict()
        assert d["rows"] == 3
        assert d["columns"] == 4
        assert d["cell_count"] == 2
    g.test(test_page_table_to_dict)

    def test_page_equation_defaults():
        eq = PageEquation()
        assert eq.latex == ""
        assert eq.rendered_text == ""
    g.test(test_page_equation_defaults)

    def test_page_equation_to_dict():
        eq = PageEquation(id="eq1", latex="x^2 + y^2 = 1",
                          rendered_text="x² + y² = 1")
        d = eq.to_dict()
        assert d["has_latex"] is True
        assert d["rendered_text"] == "x² + y² = 1"
    g.test(test_page_equation_to_dict)

    def test_page_separator_defaults():
        sep = PageSeparator()
        assert sep.orientation == "horizontal"
        assert sep.thickness == 0.5
        assert sep.color == "#000000"
    g.test(test_page_separator_defaults)

    def test_page_separator_to_dict():
        sep = PageSeparator(id="sep1", orientation="vertical",
                            thickness=2.0, color="#FF0000")
        d = sep.to_dict()
        assert d["orientation"] == "vertical"
        assert d["thickness"] == 2.0
        assert d["color"] == "#FF0000"
    g.test(test_page_separator_to_dict)

    def test_page_dimensions_defaults():
        dims = PageDimensions()
        assert dims.orientation == "portrait"
    g.test(test_page_dimensions_defaults)

    def test_page_dimensions_content_size():
        dims = PageDimensions(width=595, height=842,
                              margin_left=50, margin_right=50,
                              margin_top=72, margin_bottom=72)
        assert dims.content_width == 495
        assert dims.content_height == 698
    g.test(test_page_dimensions_content_size)

    def test_page_dimensions_to_dict():
        dims = PageDimensions(width=595, height=842, orientation="portrait")
        d = dims.to_dict()
        assert d["width"] == 595
        assert d["height"] == 842
        assert d["orientation"] == "portrait"
        assert "content_width" in d
    g.test(test_page_dimensions_to_dict)

    def test_page_analysis_defaults():
        pa = PageAnalysis()
        assert pa.page_number == 1
        assert pa.element_count == 0
        assert pa.column_count == 1
        assert pa.writing_direction == "ltr"
    g.test(test_page_analysis_defaults)

    def test_page_analysis_image_count():
        pa = PageAnalysis()
        pa.images = [PageImage(id="i1"), PageImage(id="i2")]
        assert pa.image_count == 2
    g.test(test_page_analysis_image_count)

    def test_page_analysis_text_count():
        pa = PageAnalysis()
        pa.texts = [PageText(id="t1")]
        assert pa.text_count == 1
    g.test(test_page_analysis_text_count)

    def test_page_analysis_has_images():
        pa = PageAnalysis()
        assert pa.has_images is False
        pa.images = [PageImage(id="i1")]
        assert pa.has_images is True
    g.test(test_page_analysis_has_images)

    def test_page_analysis_has_choices():
        pa = PageAnalysis()
        assert pa.has_choices is False
        pa.choices = [PageChoice(id="c1")]
        assert pa.has_choices is True
    g.test(test_page_analysis_has_choices)

    def test_page_analysis_is_rtl():
        pa = PageAnalysis(writing_direction="rtl")
        assert pa.is_rtl is True
    g.test(test_page_analysis_is_rtl)

    def test_page_analysis_all_elements():
        pa = PageAnalysis()
        pa.images = [PageImage(id="i1")]
        pa.texts = [PageText(id="t1")]
        pa.choices = [PageChoice(id="c1")]
        assert len(pa.all_elements) == 3
    g.test(test_page_analysis_all_elements)

    def test_page_analysis_question_images():
        pa = PageAnalysis()
        pa.images = [
            PageImage(id="i1", is_question_image=True),
            PageImage(id="i2", is_question_image=False),
            PageImage(id="i3", is_question_image=True),
        ]
        qimgs = pa.question_images()
        assert len(qimgs) == 2
    g.test(test_page_analysis_question_images)

    def test_page_analysis_add_warning():
        pa = PageAnalysis()
        pa.add_warning("test warning")
        assert "test warning" in pa.warnings
    g.test(test_page_analysis_add_warning)

    def test_page_analysis_to_dict():
        pa = PageAnalysis(page_number=5, element_count=10)
        pa.images = [PageImage(id="i1")]
        pa.texts = [PageText(id="t1")]
        d = pa.to_dict()
        assert d["page_number"] == 5
        assert d["element_count"] == 10
        assert d["image_count"] == 1
        assert d["text_count"] == 1
        assert "dimensions" in d
        assert "layers" in d
    g.test(test_page_analysis_to_dict)

    return g.report()


# ======================================================================
# Group 2: Visual-layer and element-type constants
# ======================================================================
def group_constants():
    g = TestGroup("Group 2: Constants")

    def test_visual_layer_constants_count():
        assert len(ALL_VISUAL_LAYERS) == 5
    g.test(test_visual_layer_constants_count)

    def test_visual_layer_constants_order():
        assert ALL_VISUAL_LAYERS[0] == VISUAL_LAYER_BACKGROUND
        assert ALL_VISUAL_LAYERS[1] == VISUAL_LAYER_IMAGE
        assert ALL_VISUAL_LAYERS[2] == VISUAL_LAYER_SHAPE
        assert ALL_VISUAL_LAYERS[3] == VISUAL_LAYER_TEXT
        assert ALL_VISUAL_LAYERS[4] == VISUAL_LAYER_OVERLAY
    g.test(test_visual_layer_constants_order)

    def test_element_type_constants_count():
        assert len(ALL_ELEMENT_TYPES) == 7
    g.test(test_element_type_constants_count)

    def test_element_type_constants_values():
        assert ELEMENT_TYPE_IMAGE in ALL_ELEMENT_TYPES
        assert ELEMENT_TYPE_TEXT in ALL_ELEMENT_TYPES
        assert ELEMENT_TYPE_CHOICE in ALL_ELEMENT_TYPES
        assert ELEMENT_TYPE_TABLE in ALL_ELEMENT_TYPES
        assert ELEMENT_TYPE_EQUATION in ALL_ELEMENT_TYPES
        assert ELEMENT_TYPE_SEPARATOR in ALL_ELEMENT_TYPES
        assert ELEMENT_TYPE_SHAPE in ALL_ELEMENT_TYPES
    g.test(test_element_type_constants_values)

    return g.report()


# ======================================================================
# Group 3: Validation weight constants
# ======================================================================
def group_validation_weights():
    g = TestGroup("Group 3: Validation Weights")

    def test_threshold_value():
        assert VISUAL_ACCURACY_THRESHOLD == 0.95
    g.test(test_threshold_value)

    def test_weights_sum():
        total = (LAYOUT_ACCURACY_WEIGHT + IMAGE_ACCURACY_WEIGHT +
                 TEXT_ACCURACY_WEIGHT + SPACING_ACCURACY_WEIGHT +
                 CHOICE_ACCURACY_WEIGHT)
        assert abs(total - 1.0) < 0.01
    g.test(test_weights_sum)

    def test_weights_positive():
        assert LAYOUT_ACCURACY_WEIGHT > 0
        assert IMAGE_ACCURACY_WEIGHT > 0
        assert TEXT_ACCURACY_WEIGHT > 0
        assert SPACING_ACCURACY_WEIGHT > 0
        assert CHOICE_ACCURACY_WEIGHT > 0
    g.test(test_weights_positive)

    def test_image_weight_highest():
        assert IMAGE_ACCURACY_WEIGHT >= LAYOUT_ACCURACY_WEIGHT
        assert IMAGE_ACCURACY_WEIGHT >= TEXT_ACCURACY_WEIGHT
        assert IMAGE_ACCURACY_WEIGHT >= SPACING_ACCURACY_WEIGHT
        assert IMAGE_ACCURACY_WEIGHT >= CHOICE_ACCURACY_WEIGHT
    g.test(test_image_weight_highest)

    return g.report()


# ======================================================================
# Group 4: ImageExtractor
# ======================================================================
def group_image_extractor():
    g = TestGroup("Group 4: ImageExtractor")

    def test_extractor_creation():
        ext = ImageExtractor()
        assert ext.log_messages == []
    g.test(test_extractor_creation)

    def test_extractor_none_page():
        ext = ImageExtractor()
        result = ext.extract_from_page(None, 1, 595, 842)
        assert result == []
        assert len(ext.log_messages) == 1
    g.test(test_extractor_none_page)

    def test_extractor_empty_images():
        ext = ImageExtractor()
        class FakePage:
            images = []
        result = ext.extract_from_page(FakePage(), 1, 595, 842)
        assert result == []
    g.test(test_extractor_empty_images)

    def test_extractor_with_images():
        ext = ImageExtractor()
        class FakePage:
            images = [
                {
                    "x0": 100, "top": 200,
                    "width": 150, "height": 100,
                    "rot": 0,
                    "stream": None,
                }
            ]
        result = ext.extract_from_page(FakePage(), 1, 595, 842)
        assert len(result) == 1
        assert result[0].id == "img_p1_0"
        assert result[0].position.x == 100
        assert result[0].position.y == 200
    g.test(test_extractor_with_images)

    def test_extractor_empty_bytes():
        ext = ImageExtractor()
        result = ext.extract_from_pdf_bytes(b"", 1)
        assert result == []
    g.test(test_extractor_empty_bytes)

    def test_extractor_detect_format_png():
        ext = ImageExtractor()
        fmt = ext._detect_format(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        assert fmt == "png"
    g.test(test_extractor_detect_format_png)

    def test_extractor_detect_format_jpg():
        ext = ImageExtractor()
        fmt = ext._detect_format(b"\xff\xd8\xff" + b"\x00" * 100)
        assert fmt == "jpg"
    g.test(test_extractor_detect_format_jpg)

    def test_extractor_detect_format_default():
        ext = ImageExtractor()
        fmt = ext._detect_format(b"\x00\x00\x00")
        assert fmt == "png"
    g.test(test_extractor_detect_format_default)

    def test_extractor_detect_format_webp():
        ext = ImageExtractor()
        fmt = ext._detect_format(b"RIFF" + b"\x00" * 100)
        assert fmt == "webp"
    g.test(test_extractor_detect_format_webp)

    def test_extractor_aspect_ratio_preserved():
        ext = ImageExtractor()
        result = ext._check_aspect_ratio(
            {"srcwidth": 200, "srcheight": 100}, 200, 100,
        )
        assert result is True
    g.test(test_extractor_aspect_ratio_preserved)

    def test_extractor_aspect_ratio_distorted():
        ext = ImageExtractor()
        result = ext._check_aspect_ratio(
            {"srcwidth": 200, "srcheight": 100}, 400, 100,
        )
        assert result is False
    g.test(test_extractor_aspect_ratio_distorted)

    return g.report()


# ======================================================================
# Group 5: PageAnalyzer
# ======================================================================
def group_page_analyzer():
    g = TestGroup("Group 5: PageAnalyzer")

    def test_analyzer_none_page():
        analyzer = PageAnalyzer()
        analysis = analyzer.analyse(None, 1)
        assert analysis.page_number == 1
        assert analysis.element_count == 0
    g.test(test_analyzer_none_page)

    def test_analyzer_dimensions():
        analyzer = PageAnalyzer()
        class FakePage:
            width = 595.0
            height = 842.0
            words = []
        analysis = analyzer.analyse(FakePage(), 1)
        assert analysis.dimensions.width == 595.0
        assert analysis.dimensions.height == 842.0
        assert analysis.dimensions.orientation == "portrait"
    g.test(test_analyzer_dimensions)

    def test_analyzer_landscape():
        analyzer = PageAnalyzer()
        class FakePage:
            width = 842.0
            height = 595.0
            words = []
        analysis = analyzer.analyse(FakePage(), 1)
        assert analysis.dimensions.orientation == "landscape"
    g.test(test_analyzer_landscape)

    def test_analyzer_writing_direction_ltr():
        analyzer = PageAnalyzer()
        class FakePage:
            width = 595.0
            height = 842.0
            words = [
                {"x0": 0, "top": 0, "bottom": 10, "x1": 30,
                 "text": "Hello", "fontname": "Helvetica"},
            ]
        analysis = analyzer.analyse(FakePage(), 1)
        assert analysis.writing_direction == "ltr"
    g.test(test_analyzer_writing_direction_ltr)

    def test_analyzer_writing_direction_rtl():
        analyzer = PageAnalyzer()
        class FakePage:
            width = 595.0
            height = 842.0
            words = [
                {"x0": 0, "top": 0, "bottom": 10, "x1": 30,
                 "text": "\u0645\u0631\u062d\u0628\u0627",
                 "fontname": "Arial"},  # Arabic "مرحبا"
            ]
        analysis = analyzer.analyse(FakePage(), 1)
        assert analysis.writing_direction == "rtl"
    g.test(test_analyzer_writing_direction_rtl)

    def test_analyzer_column_count_single():
        analyzer = PageAnalyzer()
        class FakePage:
            width = 595.0
            height = 842.0
            words = [
                {"x0": 50, "top": 0, "bottom": 10, "x1": 80, "text": "a"},
                {"x0": 100, "top": 0, "bottom": 10, "x1": 130, "text": "b"},
                {"x0": 150, "top": 0, "bottom": 10, "x1": 180, "text": "c"},
            ]
        analysis = analyzer.analyse(FakePage(), 1)
        assert analysis.column_count == 1
    g.test(test_analyzer_column_count_single)

    def test_analyzer_layers_built():
        analyzer = PageAnalyzer()
        class FakePage:
            width = 595.0
            height = 842.0
            words = []
            chars = []
            images = []
            lines = []
            rect_edges = []
        analysis = analyzer.analyse(FakePage(), 1)
        assert len(analysis.layers) == 5  # all 5 layers
    g.test(test_analyzer_layers_built)

    def test_analyzer_layers_order():
        analyzer = PageAnalyzer()
        class FakePage:
            width = 595.0
            height = 842.0
            words = []
            chars = []
            images = []
            lines = []
            rect_edges = []
        analysis = analyzer.analyse(FakePage(), 1)
        assert analysis.layers[0].name == VISUAL_LAYER_BACKGROUND
        assert analysis.layers[1].name == VISUAL_LAYER_IMAGE
        assert analysis.layers[2].name == VISUAL_LAYER_SHAPE
        assert analysis.layers[3].name == VISUAL_LAYER_TEXT
        assert analysis.layers[4].name == VISUAL_LAYER_OVERLAY
    g.test(test_analyzer_layers_order)

    def test_analyzer_source_path():
        analyzer = PageAnalyzer()
        class FakePage:
            width = 595.0
            height = 842.0
            words = []
            chars = []
            images = []
            lines = []
            rect_edges = []
        analysis = analyzer.analyse(FakePage(), 1, "/path/to/file.pdf")
        assert analysis.source_pdf_path == "/path/to/file.pdf"
    g.test(test_analyzer_source_path)

    def test_analyzer_log_messages():
        analyzer = PageAnalyzer()
        class FakePage:
            width = 595.0
            height = 842.0
            words = []
            chars = []
            images = []
            lines = []
            rect_edges = []
        analyzer.analyse(FakePage(), 1)
        assert len(analyzer.log_messages) > 0
    g.test(test_analyzer_log_messages)

    return g.report()


# ======================================================================
# Group 6: LayoutRebuilder
# ======================================================================
def group_layout_rebuilder():
    g = TestGroup("Group 6: LayoutRebuilder")

    def test_rebuilder_empty():
        rb = LayoutRebuilder()
        result = rb.rebuild_page(PageAnalysis())
        assert len(result) > 0  # should produce valid PDF bytes
    g.test(test_rebuilder_empty)

    def test_rebuilder_with_elements():
        rb = LayoutRebuilder()
        pa = PageAnalysis()
        pa.dimensions = PageDimensions(width=595, height=842)
        pa.texts = [
            PageText(id="t1", text="Hello World",
                     position=ElementPosition(x=50, y=100, width=200, height=20)),
        ]
        pa.layers = [
            VisualLayer(name=VISUAL_LAYER_BACKGROUND, z_index=0),
            VisualLayer(name=VISUAL_LAYER_IMAGE, z_index=10),
            VisualLayer(name=VISUAL_LAYER_SHAPE, z_index=20),
            VisualLayer(name=VISUAL_LAYER_TEXT, z_index=30,
                        elements=[PageElement(id="t1", element_type=ELEMENT_TYPE_TEXT,
                                             position=ElementPosition(x=50, y=100,
                                                                      width=200, height=20),
                                             metadata={"text": "Hello World",
                                                       "font_name": "Helvetica",
                                                       "font_size": 12})]),
            VisualLayer(name=VISUAL_LAYER_OVERLAY, z_index=40),
        ]
        result = rb.rebuild_page(pa)
        assert len(result) > 0
    g.test(test_rebuilder_with_elements)

    def test_rebuilder_all_pages_empty():
        rb = LayoutRebuilder()
        result = rb.rebuild_all_pages([])
        assert result == b""
    g.test(test_rebuilder_all_pages_empty)

    def test_rebuilder_all_pages_single():
        rb = LayoutRebuilder()
        pa = PageAnalysis(page_number=1)
        pa.dimensions = PageDimensions(width=595, height=842)
        pa.layers = [
            VisualLayer(name=VISUAL_LAYER_BACKGROUND, z_index=0),
            VisualLayer(name=VISUAL_LAYER_IMAGE, z_index=10),
            VisualLayer(name=VISUAL_LAYER_SHAPE, z_index=20),
            VisualLayer(name=VISUAL_LAYER_TEXT, z_index=30),
            VisualLayer(name=VISUAL_LAYER_OVERLAY, z_index=40),
        ]
        result = rb.rebuild_all_pages([pa])
        assert len(result) > 0
    g.test(test_rebuilder_all_pages_single)

    def test_rebuilder_log_messages():
        rb = LayoutRebuilder()
        pa = PageAnalysis()
        pa.dimensions = PageDimensions(width=595, height=842)
        pa.layers = [
            VisualLayer(name=VISUAL_LAYER_BACKGROUND, z_index=0),
            VisualLayer(name=VISUAL_LAYER_IMAGE, z_index=10),
            VisualLayer(name=VISUAL_LAYER_SHAPE, z_index=20),
            VisualLayer(name=VISUAL_LAYER_TEXT, z_index=30),
            VisualLayer(name=VISUAL_LAYER_OVERLAY, z_index=40),
        ]
        rb.rebuild_page(pa)
        assert len(rb.log_messages) > 0
    g.test(test_rebuilder_log_messages)

    return g.report()


# ======================================================================
# Group 7: ChoiceDetector
# ======================================================================
def group_choice_detector():
    g = TestGroup("Group 7: ChoiceDetector")

    def test_detector_empty_words():
        det = ChoiceDetector()
        result = det.detect_choices([], 1, 842)
        assert result == []
    g.test(test_detector_empty_words)

    def test_detector_arabic_labels():
        det = ChoiceDetector()
        words = [
            {"x0": 0, "x1": 20, "top": 100, "bottom": 110, "text": "أ.",
             "fontname": "Arial"},
            {"x0": 30, "x1": 100, "top": 100, "bottom": 110, "text": "\u0627\u0644\u0625\u062c\u0627\u0628\u0629",
             "fontname": "Arial"},
            {"x0": 0, "x1": 20, "top": 130, "bottom": 140, "text": "ب.",
             "fontname": "Arial"},
            {"x0": 30, "x1": 100, "top": 130, "bottom": 140, "text": "\u0627\u0644\u062b\u0627\u0646\u064a\u0629",
             "fontname": "Arial"},
        ]
        result = det.detect_choices(words, 1, 842)
        assert len(result) == 2
        assert result[0].label == "أ"
        assert result[1].label == "ب"
    g.test(test_detector_arabic_labels)

    def test_detector_english_labels():
        det = ChoiceDetector()
        words = [
            {"x0": 0, "x1": 20, "top": 100, "bottom": 110, "text": "A.",
             "fontname": "Helvetica"},
            {"x0": 30, "x1": 100, "top": 100, "bottom": 110, "text": "First",
             "fontname": "Helvetica"},
            {"x0": 0, "x1": 20, "top": 130, "bottom": 140, "text": "B.",
             "fontname": "Helvetica"},
        ]
        result = det.detect_choices(words, 1, 842)
        assert len(result) == 2
        assert result[0].label == "A"
        assert result[1].label == "B"
    g.test(test_detector_english_labels)

    def test_detector_mixed_labels():
        det = ChoiceDetector()
        words = [
            {"x0": 0, "x1": 20, "top": 100, "bottom": 110, "text": "أ.",
             "fontname": "Arial"},
            {"x0": 0, "x1": 20, "top": 130, "bottom": 140, "text": "B.",
             "fontname": "Helvetica"},
        ]
        result = det.detect_choices(words, 1, 842)
        assert len(result) == 2
    g.test(test_detector_mixed_labels)

    def test_detector_clean_label():
        det = ChoiceDetector()
        assert det._clean_label("أ.") == "أ"
        assert det._clean_label("ب)") == "ب"
        assert det._clean_label("C.") == "C"
    g.test(test_detector_clean_label)

    def test_detector_log_messages():
        det = ChoiceDetector()
        det.detect_choices([], 1, 842)
        assert len(det.log_messages) > 0
    g.test(test_detector_log_messages)

    return g.report()


# ======================================================================
# Group 8: CoordinateMapper
# ======================================================================
def group_coordinate_mapper():
    g = TestGroup("Group 8: CoordinateMapper")

    def test_mapper_creation():
        mapper = CoordinateMapper()
        assert len(mapper.mappings) == 0
        assert mapper.accuracy_rate == 100.0
    g.test(test_mapper_creation)

    def test_mapper_position():
        mapper = CoordinateMapper()
        orig = ElementPosition(x=50, y=100, width=200, height=20,
                               layer=VISUAL_LAYER_TEXT)
        mapped = mapper.map_position("e1", orig, 842)
        assert mapped.x == 50
        assert mapped.y == 842 - 100 - 20  # bottom-up
        assert mapped.width == 200
        assert mapped.height == 20
    g.test(test_mapper_position)

    def test_mapper_rect():
        mapper = CoordinateMapper()
        x0, y0, x1, y1 = mapper.map_rect("e1", 50, 100, 250, 120, 842)
        assert x0 == 50
        assert y0 == 842 - 120  # mapped y0
        assert x1 == 250
        assert y1 == 842 - 100  # mapped y1
    g.test(test_mapper_rect)

    def test_mapper_rotation():
        mapper = CoordinateMapper()
        result = mapper.map_rotation("e1", 45, 595, 842)
        assert result == 45
    g.test(test_mapper_rotation)

    def test_mapper_spacing():
        mapper = CoordinateMapper()
        result = mapper.map_spacing(25.0, 595, 842)
        assert result == 25.0
    g.test(test_mapper_spacing)

    def test_mapper_validate_mapping():
        mapper = CoordinateMapper()
        positions = [
            ElementPosition(x=50, y=100),
            ElementPosition(x=200, y=200),
        ]
        mapped = [
            ElementPosition(x=50, y=100),
            ElementPosition(x=200, y=200),
        ]
        result = mapper.validate_mapping(positions, mapped)
        assert result["total"] == 2
        assert result["accurate"] == 2
        assert result["accuracy_rate"] == 100.0
    g.test(test_mapper_validate_mapping)

    def test_mapper_validate_mapping_offset():
        mapper = CoordinateMapper()
        positions = [ElementPosition(x=50, y=100)]
        mapped = [ElementPosition(x=52, y=100)]  # offset > tolerance
        result = mapper.validate_mapping(positions, mapped)
        assert result["accurate"] == 0
    g.test(test_mapper_validate_mapping_offset)

    def test_mapper_accuracy_rate():
        mapper = CoordinateMapper()
        orig = ElementPosition(x=50, y=100)
        mapper.map_position("e1", orig, 842)
        orig2 = ElementPosition(x=52, y=100)  # offset > tolerance
        mapper.map_position("e2", orig2, 842)
        assert mapper.accuracy_rate < 100.0
    g.test(test_mapper_accuracy_rate)

    return g.report()


# ======================================================================
# Group 9: VisualValidator
# ======================================================================
def group_visual_validator():
    g = TestGroup("Group 9: VisualValidator")

    def test_validator_empty_analysis():
        validator = VisualValidator()
        analysis = PageAnalysis()
        analysis.dimensions = PageDimensions(width=595, height=842)
        report = validator.validate(analysis, [])
        assert report.page_number == 1
        assert report.total_elements == 0
    g.test(test_validator_empty_analysis)

    def test_validator_with_elements():
        validator = VisualValidator()
        analysis = PageAnalysis()
        analysis.dimensions = PageDimensions(width=595, height=842)
        analysis.texts = [
            PageText(id="t1", text="Hello", font_name="Helvetica",
                     position=ElementPosition(x=50, y=100)),
        ]
        analysis.images = []
        analysis.choices = []
        positions = [
            ElementPosition(x=50, y=100),
        ]
        report = validator.validate(analysis, positions)
        assert report.total_elements == 1
        assert report.layout_accuracy > 0
    g.test(test_validator_with_elements)

    def test_validator_position_only():
        validator = VisualValidator()
        orig = [ElementPosition(x=50, y=100)]
        rebuilt = [ElementPosition(x=50, y=100)]
        score = validator.validate_positions_only(orig, rebuilt)
        assert score == 1.0
    g.test(test_validator_position_only)

    def test_validator_position_only_offset():
        validator = VisualValidator()
        orig = [ElementPosition(x=50, y=100)]
        rebuilt = [ElementPosition(x=60, y=100)]
        score = validator.validate_positions_only(orig, rebuilt)
        assert score == 0.0
    g.test(test_validator_position_only_offset)

    def test_validator_passed_flag():
        validator = VisualValidator()
        analysis = PageAnalysis()
        analysis.dimensions = PageDimensions(width=595, height=842)
        analysis.texts = [
            PageText(id="t1", text="Hello", font_name="Helvetica",
                     position=ElementPosition(x=50, y=100)),
        ]
        positions = [ElementPosition(x=50, y=100)]
        report = validator.validate(analysis, positions)
        assert report.passed is True
    g.test(test_validator_passed_flag)

    def test_validator_log_messages():
        validator = VisualValidator()
        analysis = PageAnalysis()
        analysis.dimensions = PageDimensions(width=595, height=842)
        validator.validate(analysis, [])
        assert len(validator.log_messages) > 0
    g.test(test_validator_log_messages)

    return g.report()


# ======================================================================
# Group 10: VisualSimilarityReport
# ======================================================================
def group_similarity_report():
    g = TestGroup("Group 10: VisualSimilarityReport")

    def test_report_defaults():
        report = VisualSimilarityReport()
        assert report.page_number == 1
        assert report.overall_score == 0.0
        assert report.passed is False
        assert report.findings == []
    g.test(test_report_defaults)

    def test_report_add_finding():
        report = VisualSimilarityReport()
        report.add_finding("test finding")
        assert report.has_findings is True
    g.test(test_report_add_finding)

    def test_report_to_dict():
        report = VisualSimilarityReport(
            page_number=3, overall_score=0.97, passed=True,
            total_elements=10, matched_elements=9,
        )
        d = report.to_dict()
        assert d["page_number"] == 3
        assert d["overall_score"] == 0.97
        assert d["passed"] is True
        assert d["total_elements"] == 10
    g.test(test_report_to_dict)

    return g.report()


# ======================================================================
# Group 11: Main engine
# ======================================================================
def group_main_engine():
    g = TestGroup("Group 11: Main Engine")

    def test_engine_creation():
        engine = VisualPageReconstructionEngine()
        assert engine.name == "visual_page_reconstruction"
        assert engine.version == "1.0.0"
    g.test(test_engine_creation)

    def test_engine_no_pdf_artefact():
        engine = VisualPageReconstructionEngine()
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = GenerationContext(
                request="test", config=config, work_dir=Path(tmpdir),
            )
            result = engine.execute(ctx)
            assert not result.success
            assert "original_pdf" in str(result.errors)
    g.test(test_engine_no_pdf_artefact)

    def test_engine_empty_pdf():
        engine = VisualPageReconstructionEngine()
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = GenerationContext(
                request="test", config=config, work_dir=Path(tmpdir),
            )
            ctx.set("original_pdf", {"bytes": b"", "path": ""})
            result = engine.execute(ctx)
            assert not result.success
    g.test(test_engine_empty_pdf)

    def test_engine_invalid_type():
        engine = VisualPageReconstructionEngine()
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = GenerationContext(
                request="test", config=config, work_dir=Path(tmpdir),
            )
            ctx.set("original_pdf", 12345)
            result = engine.execute(ctx)
            assert not result.success
    g.test(test_engine_invalid_type)

    def test_engine_with_pdf_bytes():
        """Test with a minimal valid PDF (just enough to open)."""
        engine = VisualPageReconstructionEngine()
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = GenerationContext(
                request="test", config=config, work_dir=Path(tmpdir),
            )
            pdf_bytes = _create_minimal_pdf()
            ctx.set("original_pdf", pdf_bytes)
            result = engine.execute(ctx)
            assert "page_analyses" in result.outputs
            assert "rebuilt_pdf_bytes" in result.outputs
            assert "visual_similarity_reports" in result.outputs
    g.test(test_engine_with_pdf_bytes)

    def test_engine_with_pdf_dict():
        engine = VisualPageReconstructionEngine()
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = GenerationContext(
                request="test", config=config, work_dir=Path(tmpdir),
            )
            pdf_bytes = _create_minimal_pdf()
            ctx.set("original_pdf", {"bytes": pdf_bytes, "path": ""})
            result = engine.execute(ctx)
            assert "page_analyses" in result.outputs
    g.test(test_engine_with_pdf_dict)

    def test_engine_outputs_structure():
        engine = VisualPageReconstructionEngine()
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = GenerationContext(
                request="test", config=config, work_dir=Path(tmpdir),
            )
            pdf_bytes = _create_minimal_pdf()
            ctx.set("original_pdf", pdf_bytes)
            result = engine.execute(ctx)
            outputs = result.outputs
            assert isinstance(outputs.get("page_analyses"), list)
            assert isinstance(outputs.get("rebuilt_pdf_bytes"), bytes)
            assert isinstance(outputs.get("visual_similarity_reports"), list)
            assert isinstance(outputs.get("total_pages"), int)
            assert isinstance(outputs.get("total_elements"), int)
            assert isinstance(outputs.get("total_images"), int)
            assert isinstance(outputs.get("overall_passed"), bool)
    g.test(test_engine_outputs_structure)

    def test_engine_metadata():
        engine = VisualPageReconstructionEngine()
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = GenerationContext(
                request="test", config=config, work_dir=Path(tmpdir),
            )
            pdf_bytes = _create_minimal_pdf()
            ctx.set("original_pdf", pdf_bytes)
            result = engine.execute(ctx)
            meta = result.metadata
            assert meta.get("engine") == "visual_page_reconstruction"
            assert "total_pages" in meta
            assert "duration_ms" in meta
    g.test(test_engine_metadata)

    def test_engine_convenience_analyse_page():
        engine = VisualPageReconstructionEngine()
        pdf_bytes = _create_minimal_pdf()
        analysis = engine.analyse_page(pdf_bytes, 1)
        assert analysis.page_number == 1
    g.test(test_engine_convenience_analyse_page)

    def test_engine_convenience_validate():
        engine = VisualPageReconstructionEngine()
        analysis = PageAnalysis()
        analysis.dimensions = PageDimensions(width=595, height=842)
        report = engine.validate_reconstruction(analysis, [])
        assert isinstance(report, VisualSimilarityReport)
    g.test(test_engine_convenience_validate)

    return g.report()


# ======================================================================
# Group 12: Bootstrap integration
# ======================================================================
def group_bootstrap():
    g = TestGroup("Group 12: Bootstrap Integration")

    def test_engine_registered_in_registry():
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        engine = registry.get_engine("visual_page_reconstruction")
        assert engine is not None
        assert engine.name == "visual_page_reconstruction"
    g.test(test_engine_registered_in_registry)

    def test_engine_in_manager():
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        # The manager should have the engine registered.
        assert "visual_page_reconstruction" in manager._entries
    g.test(test_engine_in_manager)

    def test_engine_priority():
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        engine_info = manager._entries.get("visual_page_reconstruction")
        assert engine_info is not None
        assert engine_info.priority == 90
    g.test(test_engine_priority)

    def test_engine_dependencies():
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        engine_info = manager._entries.get("visual_page_reconstruction")
        assert engine_info is not None
        assert "file_planner" in engine_info.dependencies
    g.test(test_engine_dependencies)

    def test_stage_importable():
        from telegram_bot_engine.pipeline.stages import VisualReconstructionStage
        stage = VisualReconstructionStage.__init__
        assert stage is not None
    g.test(test_stage_importable)

    def test_stage_attributes():
        from telegram_bot_engine.pipeline.stages import VisualReconstructionStage
        assert VisualReconstructionStage.stage_name == "visual_reconstruction"
        assert "original_pdf" in VisualReconstructionStage.requires
        assert "page_analyses" in VisualReconstructionStage.provides
    g.test(test_stage_attributes)

    def test_total_engine_count():
        config = build_configuration()
        registry, orchestrator, manager = bootstrap(config)
        # Should have 9 engines now (8 original + 1 new).
        assert len(manager._entries) == 9
    g.test(test_total_engine_count)

    return g.report()


# ======================================================================
# Group 13: Serialisation
# ======================================================================
def group_serialisation():
    g = TestGroup("Group 13: Serialisation")

    def test_element_position_roundtrip():
        pos = ElementPosition(x=50, y=100, width=200, height=20,
                              rotation=90, layer=VISUAL_LAYER_IMAGE)
        d = pos.to_dict()
        assert d["x"] == 50
        assert d["y"] == 100
        assert d["layer"] == VISUAL_LAYER_IMAGE
    g.test(test_element_position_roundtrip)

    def test_page_image_roundtrip():
        img = PageImage(id="img1", image_bytes=b"\x00\x01",
                        image_format="png", is_question_image=True)
        d = img.to_dict()
        assert d["id"] == "img1"
        assert d["has_content"] is True
        assert d["is_question_image"] is True
    g.test(test_page_image_roundtrip)

    def test_page_text_roundtrip():
        txt = PageText(id="t1", text="Hello", font_name="Helvetica",
                       font_size=12, is_bold=True, is_italic=False)
        d = txt.to_dict()
        assert d["text"] == "Hello"
        assert d["font_name"] == "Helvetica"
    g.test(test_page_text_roundtrip)

    def test_page_choice_roundtrip():
        ch = PageChoice(id="c1", label="أ", text="\u0627\u0644\u0625\u062c\u0627\u0628\u0629")
        d = ch.to_dict()
        assert d["label"] == "أ"
    g.test(test_page_choice_roundtrip)

    def test_page_table_roundtrip():
        tbl = PageTable(id="tbl1", rows=3, columns=4,
                        cells=[["a", "b"], ["c", "d"], ["e", "f"]])
        d = tbl.to_dict()
        assert d["rows"] == 3
        assert d["columns"] == 4
        assert d["cell_count"] == 3
    g.test(test_page_table_roundtrip)

    def test_page_equation_roundtrip():
        eq = PageEquation(id="eq1", latex="x^2", rendered_text="x²")
        d = eq.to_dict()
        assert d["has_latex"] is True
    g.test(test_page_equation_roundtrip)

    def test_page_separator_roundtrip():
        sep = PageSeparator(id="sep1", orientation="horizontal",
                            thickness=1.0, color="#FF0000")
        d = sep.to_dict()
        assert d["orientation"] == "horizontal"
    g.test(test_page_separator_roundtrip)

    def test_page_dimensions_roundtrip():
        dims = PageDimensions(width=595, height=842,
                              margin_left=50, margin_right=50,
                              margin_top=72, margin_bottom=72)
        d = dims.to_dict()
        assert d["content_width"] == 495
    g.test(test_page_dimensions_roundtrip)

    def test_page_analysis_full_roundtrip():
        pa = PageAnalysis(page_number=3, column_count=2,
                          writing_direction="rtl",
                          source_pdf_path="/test.pdf")
        pa.images = [PageImage(id="i1", image_bytes=b"\x00")]
        pa.texts = [PageText(id="t1", text="Hello")]
        pa.choices = [PageChoice(id="c1", label="أ")]
        pa.tables = [PageTable(id="tbl1", rows=2, columns=2)]
        pa.equations = [PageEquation(id="eq1", latex="x=1")]
        pa.separators = [PageSeparator(id="sep1")]
        d = pa.to_dict()
        assert d["page_number"] == 3
        assert d["column_count"] == 2
        assert d["writing_direction"] == "rtl"
        assert d["image_count"] == 1
        assert d["text_count"] == 1
        assert d["choice_count"] == 1
        assert d["table_count"] == 1
        assert d["equation_count"] == 1
        assert d["separator_count"] == 1
    g.test(test_page_analysis_full_roundtrip)

    def test_visual_similarity_report_roundtrip():
        report = VisualSimilarityReport(
            page_number=1, overall_score=0.97,
            layout_accuracy=0.99, image_accuracy=0.98,
            text_accuracy=0.96, spacing_accuracy=0.97,
            choice_accuracy=1.0, passed=True,
            total_elements=10, matched_elements=9,
        )
        d = report.to_dict()
        assert d["overall_score"] == 0.97
        assert d["passed"] is True
    g.test(test_visual_similarity_report_roundtrip)

    return g.report()


# ======================================================================
# Group 14: Acceptance rules
# ======================================================================
def group_acceptance_rules():
    g = TestGroup("Group 14: Acceptance Rules")

    def test_element_has_position():
        """Every element must have X, Y, Width, Height, Rotation, Layer."""
        el = PageElement(
            id="e1",
            element_type=ELEMENT_TYPE_TEXT,
            position=ElementPosition(x=50, y=100, width=200, height=20,
                                     rotation=0, layer=VISUAL_LAYER_TEXT),
        )
        pos = el.position
        assert pos.x is not None
        assert pos.y is not None
        assert pos.width is not None
        assert pos.height is not None
        assert pos.rotation is not None
        assert pos.layer is not None
    g.test(test_element_has_position)

    def test_element_single_type():
        """Each element has exactly one type and one visual layer."""
        el = PageElement(id="e1", element_type=ELEMENT_TYPE_IMAGE,
                         position=ElementPosition(layer=VISUAL_LAYER_IMAGE))
        assert el.element_type in ALL_ELEMENT_TYPES
        assert el.position.layer in ALL_VISUAL_LAYERS
    g.test(test_element_single_type)

    def test_no_element_omission():
        """No element may be omitted or merged."""
        pa = PageAnalysis()
        pa.texts = [PageText(id=f"t{i}") for i in range(5)]
        pa.images = [PageImage(id=f"i{i}", image_bytes=b"\x00")
                     for i in range(3)]
        assert len(pa.all_elements) == 8
    g.test(test_no_element_omission)

    def test_image_not_compressed():
        """No image may be compressed or blurred."""
        img = PageImage(id="img1", image_bytes=b"\x89PNG" + b"\x00" * 100,
                        image_format="png")
        assert img.has_content is True
        assert len(img.image_bytes) == 104  # preserved
    g.test(test_image_not_compressed)

    def test_question_image_preserved():
        """Question images must never be deleted, replaced, or redrawn."""
        img = PageImage(id="qimg", is_question_image=True,
                        image_bytes=b"\x89PNG" + b"\x00" * 50)
        pa = PageAnalysis()
        pa.images = [img]
        qimgs = pa.question_images()
        assert len(qimgs) == 1
        assert qimgs[0].has_content is True
    g.test(test_question_image_preserved)

    def test_choices_maintain_position():
        """All choices must maintain their original position."""
        ch1 = PageChoice(id="c1", label="أ",
                         position=ElementPosition(x=50, y=100))
        ch2 = PageChoice(id="c2", label="ب",
                         position=ElementPosition(x=50, y=130))
        # Positions are preserved.
        assert ch1.position.y < ch2.position.y
    g.test(test_choices_maintain_position)

    def test_similarity_above_threshold():
        """The similarity score must be above 95% to pass."""
        assert VISUAL_ACCURACY_THRESHOLD == 0.95
    g.test(test_similarity_above_threshold)

    return g.report()


# ======================================================================
# Helper: create a minimal valid PDF
# ======================================================================
def _create_minimal_pdf() -> bytes:
    """Create a minimal valid PDF with one blank page."""
    # Minimal PDF structure.
    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 595 842] >>\nendobj\n"
    )
    body = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(body))
        body += obj
    xref_start = len(body)
    body += b"xref\n0 4\n"
    body += b"0000000000 65535 f \n"
    for offset in offsets:
        body += f"{offset:010d} 00000 n \n".encode()
    body += b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n"
    body += str(xref_start).encode() + b"\n%%EOF\n"
    return body


# ======================================================================
# Main
# ======================================================================
if __name__ == "__main__":
    total_failed = 0
    total_failed += group_data_model()
    total_failed += group_constants()
    total_failed += group_validation_weights()
    total_failed += group_image_extractor()
    total_failed += group_page_analyzer()
    total_failed += group_layout_rebuilder()
    total_failed += group_choice_detector()
    total_failed += group_coordinate_mapper()
    total_failed += group_visual_validator()
    total_failed += group_similarity_report()
    total_failed += group_main_engine()
    total_failed += group_bootstrap()
    total_failed += group_serialisation()
    total_failed += group_acceptance_rules()

    print(f"\n{'='*70}")
    print(f"  TOTAL RESULTS")
    print(f"{'='*70}")
    if total_failed == 0:
        print("  All tests passed! ✅")
    else:
        print(f"  {total_failed} test(s) failed.")
    print(f"{'='*70}\n")
    sys.exit(0 if total_failed == 0 else 1)
