"""
Choice Detector — detects and validates multiple-choice options on a
PDF page.

The :class:`ChoiceDetector` is a stateless helper that the
:class:`PageAnalyzer` uses to identify all multiple-choice labels and
their associated text content.  It handles both Arabic (أ، ب، ج، د)
and English (A, B, C, D) choice formats.

Acceptance rules
----------------
* All choices must be detected — none may be missed.
* Each choice must preserve its original position, order, spacing,
  and shape.
* Choices must maintain the same relative distance between each other.
* No choice may be reordered or merged with another.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from .page_analysis import (
    PageChoice,
    ElementPosition,
    VISUAL_LAYER_TEXT,
)


class ChoiceDetector:
    """Detects multiple-choice options from page words.

    The detector scans the words extracted from a PDF page and
    identifies patterns that match multiple-choice labels.  It then
    groups each label with its associated text content.
    """

    # Arabic choice labels (including extended forms)
    ARABIC_LABELS: List[str] = [
        "أ", "ب", "ج", "د", "هـ", "و", "ز", "ح", "ط", "ي",
    ]

    # English choice labels
    ENGLISH_LABELS: List[str] = [
        "A", "B", "C", "D", "E", "F", "G", "H",
    ]

    # Patterns for matching choice labels
    ARABIC_PATTERN = re.compile(
        r"^[أ-ي]\s*[\.\)\:]\s*$|"
        r"^[أ-ي]\)\s*$|"
        r"^[\(（][أ-ي][\)）]\s*$|"
        r"^[أ-ي]\.\s*$|"
        r"^[أ-ي]$"
    )

    ENGLISH_PATTERN = re.compile(
        r"^[A-Ha-h]\s*[\.\)\:]\s*$|"
        r"^[A-Ha-h]\)\s*$|"
        r"^[\(（][A-Ha-h][\)）]\s*$|"
        r"^[A-Ha-h]\.\s*$|"
        r"^[A-Ha-h]$"
    )

    def __init__(self) -> None:
        self._log_messages: List[str] = []

    @property
    def log_messages(self) -> List[str]:
        return list(self._log_messages)

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def detect_choices(
        self,
        words: List[Dict[str, Any]],
        page_number: int,
        page_height: float,
    ) -> List[PageChoice]:
        """Detect all multiple-choice options from a list of words.

        Parameters:
            words: The list of word dicts from pdfplumber
                (each with ``x0``, ``x1``, ``top``, ``bottom``,
                ``text``, ``fontname``, etc.).
            page_number: The 1-based page number.
            page_height: The page height in points.

        Returns:
            A list of :class:`PageChoice` objects.
        """
        choices: List[PageChoice] = []
        if not words:
            self._log_messages.append(
                f"ChoiceDetector: page {page_number} has no words.",
            )
            return choices

        # Find all choice labels.
        label_indices = self._find_labels(words)
        self._log_messages.append(
            f"ChoiceDetector: page {page_number} found "
            f"{len(label_indices)} choice label(s)."
        )

        # Build choice objects.
        for label_idx in label_indices:
            word = words[label_idx]
            label_text = word.get("text", "").strip()
            label = self._clean_label(label_text)

            # Find the text associated with this choice.
            text_content = self._find_choice_text(
                words, label_idx, label_indices,
            )

            choice_id = f"choice_p{page_number}_{len(choices)}"
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
                text=text_content,
                metadata={
                    "page_number": page_number,
                    "word_index": label_idx,
                    "font_name": word.get("fontname", ""),
                },
            ))

        # Validate ordering.
        self._validate_ordering(choices, words)

        return choices

    def detect_in_analysis(
        self, words: List[Dict[str, Any]], page_number: int,
        page_height: float,
    ) -> List[PageChoice]:
        """Alias for :meth:`detect_choices` for consistency."""
        return self.detect_choices(words, page_number, page_height)

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _find_labels(self, words: List[Dict[str, Any]]) -> List[int]:
        """Find the indices of all choice labels in the word list."""
        label_indices: List[int] = []
        seen_labels: Set[str] = set()

        for idx, word in enumerate(words):
            text = word.get("text", "").strip()
            if not text:
                continue
            if (
                (self.ARABIC_PATTERN.match(text) or
                 self.ENGLISH_PATTERN.match(text)) and
                text not in seen_labels
            ):
                label_indices.append(idx)
                seen_labels.add(text)

        return label_indices

    def _clean_label(self, text: str) -> str:
        """Clean a choice label by removing punctuation."""
        return text.strip(".):(")

    def _find_choice_text(
        self,
        words: List[Dict[str, Any]],
        label_idx: int,
        label_indices: List[int],
    ) -> str:
        """Find the text content associated with a choice label.

        The text content is the word(s) immediately following the
        label on the same line.
        """
        if label_idx + 1 >= len(words):
            return ""

        label_word = words[label_idx]
        label_top = float(label_word.get("top", 0))
        label_bottom = float(label_word.get("bottom", 0))
        label_height = label_bottom - label_top

        # Find words on the same line.
        text_parts: List[str] = []
        next_idx = label_idx + 1

        # Stop at the next label.
        next_label_idx = -1
        for li in label_indices:
            if li > label_idx:
                next_label_idx = li
                break

        while next_idx < len(words):
            word = words[next_idx]
            word_top = float(word.get("top", 0))
            word_bottom = float(word.get("bottom", 0))
            word_height = word_bottom - word_top

            # Same line check (within 50% of line height tolerance).
            tolerance = max(label_height, word_height) * 0.5
            if abs(word_top - label_top) > tolerance:
                break

            # Stop before the next label.
            if next_label_idx >= 0 and next_idx >= next_label_idx:
                break

            text_parts.append(word.get("text", ""))
            next_idx += 1

        return " ".join(text_parts)

    def _validate_ordering(
        self, choices: List[PageChoice], words: List[Dict[str, Any]],
    ) -> None:
        """Validate that choices maintain their original order.

        Choices should appear in the same order as in the original
        document.  If they are out of order, a warning is logged.
        """
        if len(choices) < 2:
            return

        for i in range(len(choices) - 1):
            curr = choices[i]
            next_choice = choices[i + 1]
            if curr.position.y > next_choice.position.y + 5:
                # The next choice is significantly above the current
                # one — this might indicate reordering.
                self._log_messages.append(
                    f"ChoiceDetector: possible ordering issue at "
                    f"choice '{curr.label}' (y={curr.position.y}) "
                    f"vs '{next_choice.label}' (y={next_choice.position.y})."
                )


__all__ = ["ChoiceDetector"]
