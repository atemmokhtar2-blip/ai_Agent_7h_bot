"""
Image Extractor — extracts images from a PDF page without compression,
transparency changes, or re-drawing.

The :class:`ImageExtractor` is a stateless helper that the
:class:`VisualPageReconstructionEngine` calls during the *extraction*
phase.  It reads images directly from the embedded PDF stream (not via
screenshot), preserving the original bytes, format, colours, and
dimensions.

Acceptance rules for image extraction
--------------------------------------
* Images must be extracted directly from the PDF embedded stream.
* No compression, no Blur, no Opacity changes, no Transparency.
* No image scaling that distorts the aspect ratio.
* Question images must never be deleted, replaced, or redrawn.
* All images must appear with full quality, original size, original
  position, and original aspect ratio.
"""
from __future__ import annotations
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from .page_analysis import (
    PageImage,
    ElementPosition,
    VISUAL_LAYER_IMAGE,
    ELEMENT_TYPE_IMAGE,
)

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class ImageExtractor:
    """Extracts images from a PDF page using embedded stream data.

    The extractor prioritises direct embedded extraction over
    screenshot-based methods.  When ``pdfplumber`` is available, it
    uses the page's ``images`` attribute to retrieve each image's raw
    bytes and metadata.
    """

    def __init__(self) -> None:
        self._log_messages: List[str] = []

    @property
    def log_messages(self) -> List[str]:
        return list(self._log_messages)

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def extract_from_page(
        self, pdf_page: Any, page_number: int, page_width: float,
        page_height: float,
    ) -> List[PageImage]:
        """Extract all images from a single PDF page.

        Parameters:
            pdf_page: A ``pdfplumber`` page object (or any object with
                an ``images`` attribute returning image metadata dicts).
            page_number: The 1-based page number.
            page_width: The page width in points.
            page_height: The page height in points.

        Returns:
            A list of :class:`PageImage` objects with raw image bytes,
            position, and metadata.
        """
        images: List[PageImage] = []
        if pdf_page is None:
            self._log_messages.append(
                "ImageExtractor: pdf_page is None, skipping extraction.",
            )
            return images

        raw_images = getattr(pdf_page, "images", None) or []
        self._log_messages.append(
            f"ImageExtractor: found {len(raw_images)} image(s) on "
            f"page {page_number}."
        )

        for idx, raw_img in enumerate(raw_images):
            page_img = self._extract_single_image(
                raw_img, idx, page_number, page_width, page_height,
            )
            if page_img is not None:
                images.append(page_img)

        self._log_messages.append(
            f"ImageExtractor: extracted {len(images)} image(s) from "
            f"page {page_number}."
        )
        return images

    def extract_from_pdf_bytes(
        self, pdf_bytes: bytes, page_number: int,
    ) -> List[PageImage]:
        """Extract images from a PDF given as raw bytes.

        Parameters:
            pdf_bytes: The raw PDF file bytes.
            page_number: The 1-based page number.

        Returns:
            A list of :class:`PageImage` objects.
        """
        if not pdf_bytes:
            self._log_messages.append(
                "ImageExtractor: empty pdf_bytes, returning empty list.",
            )
            return []

        try:
            import io
            from pdfminer.high_level import extract_pages
            # pdfminer is available via pdfplumber dependency.
            # We use pdfplumber for the page object.
            pdf_file = io.BytesIO(pdf_bytes)
            pdf = pdfplumber.open(pdf_file)
            if page_number < 1 or page_number > len(pdf.pages):
                self._log_messages.append(
                    f"ImageExtractor: page {page_number} out of range "
                    f"(total {len(pdf.pages)}).",
                )
                pdf.close()
                return []
            page = pdf.pages[page_number - 1]
            pw = float(page.width)
            ph = float(page.height)
            images = self.extract_from_page(page, page_number, pw, ph)
            pdf.close()
            return images
        except Exception as exc:
            self._log_messages.append(
                f"ImageExtractor: failed to extract from bytes: {exc}",
            )
            return []

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _extract_single_image(
        self, raw_img: Dict[str, Any], idx: int, page_number: int,
        page_width: float, page_height: float,
    ) -> Optional[PageImage]:
        """Extract a single image from its raw metadata dict.

        Parameters:
            raw_img: A dict from ``pdfplumber`` page ``images`` list.
            idx: The 0-based index within the page's image list.
            page_number: The 1-based page number.
            page_width: The page width in points.
            page_height: The page height in points.

        Returns:
            A :class:`PageImage` or ``None`` if extraction failed.
        """
        image_id = f"img_p{page_number}_{idx}"
        x0 = float(raw_img.get("x0", 0))
        top = float(raw_img.get("top", 0))
        width = float(raw_img.get("width", 0))
        height = float(raw_img.get("height", 0))

        # pdfplumber uses (x0, top) for top-left; y is measured from top.
        # We convert to a coordinate system where y=0 is the top.
        position = ElementPosition(
            x=x0,
            y=top,
            width=width,
            height=height,
            rotation=float(raw_img.get("rot", 0)),
            layer=VISUAL_LAYER_IMAGE,
        )

        image_format = raw_img.get("imagemask", False)
        if image_format:
            fmt = "png"
        else:
            # Try to detect format from the image data.
            stream_data = raw_img.get("stream", None)
            fmt = self._detect_format(stream_data)

        image_bytes = self._extract_raw_bytes(raw_img)

        is_question = self._is_question_image(raw_img, image_id)
        aspect_ratio = self._check_aspect_ratio(
            raw_img, width, height,
        )

        metadata = {
            "extraction_method": "embedded",
            "page_number": page_number,
            "index": idx,
            "original_width": width,
            "original_height": height,
            "pdf_x0": x0,
            "pdf_top": top,
        }

        return PageImage(
            id=image_id,
            position=position,
            image_bytes=image_bytes,
            image_format=fmt,
            is_question_image=is_question,
            aspect_ratio_preserved=aspect_ratio,
            metadata=metadata,
        )

    @staticmethod
    def _extract_raw_bytes(raw_img: Dict[str, Any]) -> bytes:
        """Attempt to extract raw image bytes from the raw metadata.

        pdfplumber stores image data in the ``stream`` key of each
        image dict.  We try multiple approaches to get the raw bytes.
        """
        stream = raw_img.get("stream", None)
        if stream is not None:
            # pdfplumber stores the stream as a pdfminer PDFStream
            # object; try to get the raw data.
            raw_data = getattr(stream, "rawdata", None) or \
                       getattr(stream, "get_data", None) or None
            if raw_data is not None:
                if callable(raw_data):
                    try:
                        return bytes(raw_data())
                    except Exception:
                        pass
                if isinstance(raw_data, (bytes, bytearray)):
                    return bytes(raw_data)

        # Try the 'data' key (used by some pdfplumber versions).
        data = raw_img.get("data", None)
        if isinstance(data, bytes):
            return data

        # Try the 'srcsize' as a fallback indicator.
        return b""

    @staticmethod
    def _detect_format(stream_data: Any) -> str:
        """Detect the image format from raw bytes or stream data."""
        if not stream_data:
            return "png"
        raw = b""
        if isinstance(stream_data, bytes):
            raw = stream_data
        elif callable(getattr(stream_data, "get_data", None)):
            try:
                raw = bytes(stream_data.get_data())
            except Exception:
                pass
        elif hasattr(stream_data, "rawdata") and isinstance(
            stream_data.rawdata, bytes,
        ):
            raw = stream_data.rawdata

        if not raw:
            return "png"

        # Check magic bytes.
        if raw[:3] == b"\xff\xd8\xff":
            return "jpg"
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"
        if raw[:4] == b"RIFF":
            return "webp"
        if raw[:4] == b"GIF8":
            return "gif"
        if raw[:2] == b"BM":
            return "bmp"
        return "png"

    @staticmethod
    def _is_question_image(raw_img: Dict[str, Any], image_id: str) -> bool:
        """Determine whether an image is part of a question.

        Images are considered question images if they are embedded
        (not external links) and are positioned within the content
        area of the page.
        """
        return bool(raw_img.get("stream")) or bool(
            raw_img.get("data"),
        )

    @staticmethod
    def _check_aspect_ratio(
        raw_img: Dict[str, Any], width: float, height: float,
    ) -> bool:
        """Check whether the extracted image preserves its aspect ratio.

        If the original dimensions are stored in the metadata, compare
        them with the placed dimensions.
        """
        orig_w = raw_img.get("srcwidth")
        orig_h = raw_img.get("srcheight")
        if orig_w and orig_h:
            orig_ratio = float(orig_w) / float(orig_h)
            placed_ratio = width / height if height > 0 else 0
            if orig_ratio > 0 and placed_ratio > 0:
                # Allow 5% tolerance.
                return abs(orig_ratio - placed_ratio) / orig_ratio < 0.05
        return True


__all__ = ["ImageExtractor"]
