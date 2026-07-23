"""
Coordinate Mapper — ensures pixel-accurate coordinate mapping between
the original PDF and the rebuilt output.

The :class:`CoordinateMapper` is a stateless helper that the
:class:`LayoutRebuilder` uses to convert coordinates between the
original PDF coordinate system and the output PDF coordinate system.
It ensures that every element is placed at exactly the same position
in the output as it was in the original.

Acceptance rules
----------------
* No element may change position, size, or rotation.
* The coordinate mapping must be bi-directional and lossless.
* Margins, spacing, and alignment must be preserved exactly.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from .page_analysis import ElementPosition


@dataclass
class CoordinateMapping:
    """A single coordinate mapping entry.
    Attributes:
        element_id: The element identifier.
        original: The original position.
        mapped: The mapped position.
        delta_x: The horizontal offset (should be 0).
        delta_y: The vertical offset (should be 0).
        is_accurate: ``True`` when the delta is within tolerance.
    """
    element_id: str = ""
    original: ElementPosition = field(default_factory=ElementPosition)
    mapped: ElementPosition = field(default_factory=ElementPosition)
    delta_x: float = 0.0
    delta_y: float = 0.0
    is_accurate: bool = True


class CoordinateMapper:
    """Maps coordinates between original and output PDF pages.

    The mapper supports three coordinate systems:
    1. PDF native (origin at bottom-left, y-axis pointing up).
    2. Top-down (origin at top-left, y-axis pointing down — used by
       pdfplumber).
    3. Output canvas (origin at bottom-left, matching ReportLab).
    """

    # Tolerance for pixel-accurate matching (in points).
    POSITION_TOLERANCE: float = 0.5
    SIZE_TOLERANCE: float = 0.5
    ROTATION_TOLERANCE: float = 0.5

    def __init__(self) -> None:
        self._mappings: List[CoordinateMapping] = []
        self._log_messages: List[str] = []

    @property
    def mappings(self) -> List[CoordinateMapping]:
        return list(self._mappings)

    @property
    def log_messages(self) -> List[str]:
        return list(self._log_messages)

    @property
    def accuracy_rate(self) -> float:
        """The percentage of mappings that are within tolerance."""
        if not self._mappings:
            return 100.0
        accurate = sum(1 for m in self._mappings if m.is_accurate)
        return (accurate / len(self._mappings)) * 100.0

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def map_position(
        self,
        element_id: str,
        original: ElementPosition,
        page_height: float,
    ) -> ElementPosition:
        """Map a position from top-down to PDF native coordinates.

        Parameters:
            element_id: The element identifier.
            original: The original position (top-down coordinate system).
            page_height: The page height in points.

        Returns:
            The mapped position (PDF native coordinate system).
        """
        # Convert from top-down to bottom-up.
        mapped_y = page_height - original.y - original.height
        mapped = ElementPosition(
            x=original.x,
            y=mapped_y,
            width=original.width,
            height=original.height,
            rotation=original.rotation,
            layer=original.layer,
        )

        delta_x = abs(mapped.x - original.x)
        delta_y = abs(mapped.y - original.y)
        is_accurate = (
            delta_x <= self.POSITION_TOLERANCE and
            delta_y <= self.POSITION_TOLERANCE
        )

        mapping = CoordinateMapping(
            element_id=element_id,
            original=original,
            mapped=mapped,
            delta_x=delta_x,
            delta_y=delta_y,
            is_accurate=is_accurate,
        )
        self._mappings.append(mapping)

        if not is_accurate:
            self._log_messages.append(
                f"CoordinateMapper: element '{element_id}' has delta "
                f"x={delta_x:.2f}, y={delta_y:.2f}."
            )

        return mapped

    def map_rect(
        self,
        element_id: str,
        x0: float, y0: float, x1: float, y1: float,
        page_height: float,
    ) -> Tuple[float, float, float, float]:
        """Map a rectangle from top-down to PDF native coordinates.

        Parameters:
            element_id: The element identifier.
            x0, y0, x1, y1: The rectangle corners in top-down coords.
            page_height: The page height in points.

        Returns:
            The mapped rectangle (x0, y0, x1, y1) in PDF native coords.
        """
        mapped_y0 = page_height - y1
        mapped_y1 = page_height - y0

        width = x1 - x0
        height = y1 - y0
        original = ElementPosition(x=x0, y=y0, width=width, height=height)
        mapped = ElementPosition(
            x=x0, y=mapped_y0, width=width, height=height,
        )

        delta_x = abs(mapped.x - original.x)
        delta_y = abs(mapped.y - original.y)
        is_accurate = (
            delta_x <= self.POSITION_TOLERANCE and
            delta_y <= self.POSITION_TOLERANCE
        )

        mapping = CoordinateMapping(
            element_id=element_id,
            original=original,
            mapped=mapped,
            delta_x=delta_x,
            delta_y=delta_y,
            is_accurate=is_accurate,
        )
        self._mappings.append(mapping)

        return x0, mapped_y0, x1, mapped_y1

    def validate_mapping(
        self,
        original_positions: List[ElementPosition],
        mapped_positions: List[ElementPosition],
        tolerance: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Validate that all mappings are within tolerance.

        Parameters:
            original_positions: The original positions.
            mapped_positions: The mapped positions.
            tolerance: The tolerance in points (defaults to
                ``POSITION_TOLERANCE``).

        Returns:
            A dict with ``total``, ``accurate``, ``inaccurate``, and
            ``accuracy_rate`` keys.
        """
        tol = tolerance or self.POSITION_TOLERANCE
        total = len(original_positions)
        accurate = 0
        inaccurate_ids: List[str] = []

        for i in range(total):
            orig = original_positions[i]
            mapped = mapped_positions[i]
            dx = abs(mapped.x - orig.x)
            dy = abs(mapped.y - orig.y)
            if dx <= tol and dy <= tol:
                accurate += 1
            else:
                inaccurate_ids.append(f"element_{i}")
                self._log_messages.append(
                    f"CoordinateMapper: validation failed for "
                    f"element_{i} (dx={dx:.2f}, dy={dy:.2f})."
                )

        accuracy_rate = (accurate / total * 100) if total > 0 else 100.0

        return {
            "total": total,
            "accurate": accurate,
            "inaccurate": total - accurate,
            "accuracy_rate": accuracy_rate,
            "inaccurate_ids": inaccurate_ids,
        }

    def map_rotation(
        self,
        element_id: str,
        original_rotation: float,
        page_width: float,
        page_height: float,
    ) -> float:
        """Map a rotation angle between coordinate systems.

        Parameters:
            element_id: The element identifier.
            original_rotation: The original rotation in degrees.
            page_width: The page width in points.
            page_height: The page height in points.

        Returns:
            The mapped rotation in degrees (same value for most cases).
        """
        # Rotation is generally the same in both coordinate systems
        # for text and images.  For shapes, the rotation might need
        # to be mirrored.
        return original_rotation

    def map_spacing(
        self,
        original_spacing: float,
        page_width: float,
        page_height: float,
    ) -> float:
        """Map spacing between elements.

        Spacing is preserved as-is in both coordinate systems.

        Parameters:
            original_spacing: The original spacing in points.
            page_width: The page width in points.
            page_height: The page height in points.

        Returns:
            The mapped spacing (same value).
        """
        return original_spacing


__all__ = ["CoordinateMapper", "CoordinateMapping"]
