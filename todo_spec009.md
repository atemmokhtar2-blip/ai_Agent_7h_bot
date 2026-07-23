# Specification 009 — PDFX AI Visual Page Reconstruction Engine

## Status
**COMPLETED** — July 2026

## Description
The PDFX AI Visual Page Reconstruction Engine is a pixel-accurate PDF
page reconstruction engine.  It reads a PDF file, analyses every
element on every page (images, text, choices, tables, equations,
separators), and produces a rebuilt PDF that is visually
indistinguishable from the original.

The engine follows the core principle: **"The original is the
reference."**  No re-design, no visual improvement, no layout changes.

## Pipeline Position
- **After**: file_planner (Specification 008)
- **Before**: optional (standalone or integrated into generate stage)
- **Priority**: 90
- **Engine ID**: `visual_page_reconstruction`

## Engines

| Engine | Name | Version | Description |
|--------|------|---------|-------------|
| VisualPageReconstructionEngine | visual_page_reconstruction | 1.0.0 | Pixel-accurate PDF page reconstruction |

## Helpers

| Helper | File | Description |
|--------|------|-------------|
| ImageExtractor | image_extractor.py | Extracts images from PDF embedded streams |
| PageAnalyzer | page_analyzer.py | Analyses every element on a PDF page |
| LayoutRebuilder | layout_rebuilder.py | Rebuilds pages with pixel-accurate fidelity |
| ChoiceDetector | choice_detector.py | Detects multiple-choice options |
| CoordinateMapper | coordinate_mapper.py | Maps coordinates between systems |
| VisualValidator | visual_validator.py | Validates rebuilt pages against originals |

## Data Model

| Class | File | Description |
|-------|------|-------------|
| PageAnalysis | page_analysis.py | Complete analysis of a single PDF page |
| PageElement | page_analysis.py | A single element on a page |
| ElementPosition | page_analysis.py | Position and geometry of an element |
| VisualLayer | page_analysis.py | Visual layer descriptor for rendering order |
| PageImage | page_analysis.py | An image element extracted from the PDF |
| PageText | page_analysis.py | A text element on the PDF |
| PageChoice | page_analysis.py | A multiple-choice option |
| PageTable | page_analysis.py | A table element on the PDF |
| PageEquation | page_analysis.py | A mathematical equation |
| PageSeparator | page_analysis.py | A separator line |
| PageDimensions | page_analysis.py | Physical dimensions of a page |
| VisualSimilarityReport | visual_validator.py | Validation report |
| CoordinateMapping | coordinate_mapper.py | Coordinate mapping entry |

## Visual Layers (rendering order)

1. `VISUAL_LAYER_BACKGROUND` — page background (z_index=0)
2. `VISUAL_LAYER_IMAGE` — images (z_index=10)
3. `VISUAL_LAYER_SHAPE` — vector shapes (z_index=20)
4. `VISUAL_LAYER_TEXT` — all text content (z_index=30)
5. `VISUAL_LAYER_OVERLAY` — overlays, watermarks (z_index=40)

## Element Types

| Type | Constant | Description |
|------|----------|-------------|
| image | ELEMENT_TYPE_IMAGE | Embedded images |
| text | ELEMENT_TYPE_TEXT | Text content |
| choice | ELEMENT_TYPE_CHOICE | Multiple-choice options |
| table | ELEMENT_TYPE_TABLE | Tables |
| equation | ELEMENT_TYPE_EQUATION | Mathematical equations |
| separator | ELEMENT_TYPE_SEPARATOR | Separator lines |
| shape | ELEMENT_TYPE_SHAPE | Vector shapes |

## Validation Weights

| Metric | Weight | Threshold |
|--------|--------|-----------|
| Layout accuracy | 20% | 98% |
| Image accuracy | 30% | 98% |
| Text accuracy | 25% | 98% |
| Spacing accuracy | 15% | 98% |
| Choice accuracy | 10% | 98% |
| **Overall** | **100%** | **95%** |

## Files Created

| File | Description |
|------|-------------|
| engines/generators/visual_page_reconstruction/__init__.py | Package init |
| engines/generators/visual_page_reconstruction/page_analysis.py | Data model |
| engines/generators/visual_page_reconstruction/image_extractor.py | Image extraction |
| engines/generators/visual_page_reconstruction/page_analyzer.py | Page analysis |
| engines/generators/visual_page_reconstruction/layout_rebuilder.py | Layout reconstruction |
| engines/generators/visual_page_reconstruction/choice_detector.py | Choice detection |
| engines/generators/visual_page_reconstruction/coordinate_mapper.py | Coordinate mapping |
| engines/generators/visual_page_reconstruction/visual_validator.py | Visual validation |
| engines/generators/visual_page_reconstruction/page_reconstruction_engine.py | Main engine |
| pipeline/stages/visual_reconstruction_stage.py | Pipeline stage |

## Integration Points

- Registered in `engines/generators/__init__.py`
- Registered in `core/bootstrap.py` (registry + manager)
- Registered in `pipeline/stages/__init__.py`
- Pipeline stage: `visual_reconstruction_stage.py`

## Acceptance Rules

1. Every element must have X, Y, Width, Height, Rotation, Layer.
2. No element may be omitted or merged.
3. Images must come from embedded PDF streams (not screenshots).
4. No image may be compressed, blurred, or have opacity changed.
5. All choices must maintain their original position, order, spacing,
   and shape.
6. The similarity score must be above 95% to pass validation.
7. The engine reads only the `original_pdf` artefact.
8. The engine does not create project files on disk.
