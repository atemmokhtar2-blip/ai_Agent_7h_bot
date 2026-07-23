"""
Stage 1 — Text cleaning.

Responsibilities:
    * Normalise whitespace (collapse runs of spaces/tabs, trim ends).
    * Normalise line endings.
    * Normalise Arabic characters (e.g. ﻷ → لأ, ﻯ → ي).
    * Remove common noise (zero-width characters, emoji codes).
    * Fix common typographic issues (smart quotes → straight quotes).

The cleaned text is stored in ``report.cleaned_request`` and the
original in ``report.raw_request``.  A list of the cleaning operations
performed is stored in ``state["cleaning_notes"]`` for traceability.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List

from ..analysis_report import AnalysisReport


# ---------------------------------------------------------------------------#
# Character normalisation maps
# ---------------------------------------------------------------------------#

# Smart / curly quotes → straight
_QUOTE_MAP: Dict[str, str] = {
    "\u2018": "'",   # ‘
    "\u2019": "'",   # ’
    "\u201C": '"',   # “
    "\u201D": '"',   # ”
    "\u2033": '"',   # ″
    "\u2032": "'",   # ′
    "\u00ab": '"',   # «
    "\u00bb": '"',   # »
    "\u201e": '"',   # „
    "\u201a": "'",   # ‚
}

# Common Arabic ligatures → decomposed forms
_ARABIC_LIGATURE_MAP: Dict[str, str] = {
    "\ufb56": "\u067b",  # ﭖ → ٳ (Persian peh — decompose)
    "\ufb58": "\u067b",
    "\ufb7a": "\u067e",
    "\ufb7c": "\u067e",
    "\ufef5": "\u0644\u0627",  # ﻵ → لا
    "\ufef6": "\u0644\u0627",
    "\ufef7": "\u0644\u0623",  # ﻷ → لأ
    "\ufef8": "\u0644\u0623",
    "\ufef9": "\u0644\u0625",  # ﻹ → لإ
    "\ufefa": "\u0644\u0625",
    "\ufefb": "\u0644\u064a",  # ﻻ → لي
    "\ufefc": "\u0644\u064a",
    "\u0649": "\u064a",  # ى → ي  (alef maksura → yeh)
}

# Zero-width and invisible characters to strip
_INVISIBLE_RE = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f\ufeff\u2060\u2061\u2062\u2063\ufe0f]"
)


def _normalise_quotes(text: str) -> str:
    for old, new in _QUOTE_MAP.items():
        text = text.replace(old, new)
    return text


def _normalise_arabic(text: str) -> str:
    for old, new in _ARABIC_LIGATURE_MAP.items():
        text = text.replace(old, new)
    return text


def _collapse_whitespace(text: str) -> str:
    # Normalise line endings first
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Replace tabs with spaces
    text = text.replace("\t", " ")
    # Collapse runs of spaces
    text = re.sub(r"[ ]{2,}", " ", text)
    # Collapse runs of newlines (3+ → 2)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Trim each line
    text = "\n".join(line.strip() for line in text.split("\n"))
    # Trim overall
    return text.strip()


def _remove_invisible(text: str) -> str:
    return _INVISIBLE_RE.sub("", text)


def _normalise_unicode(text: str) -> str:
    """Apply NFKC normalisation to unify compatibility characters."""
    return unicodedata.normalize("NFKC", text)


# ---------------------------------------------------------------------------#
# Main entry
# ---------------------------------------------------------------------------#

def run(state: Dict, report: AnalysisReport) -> List[str]:
    """Clean the raw request text.

    Writes:
        report.raw_request     ← the original request (unchanged).
        report.cleaned_request ← the cleaned request.
        state["cleaning_notes"] ← list of operations performed.
    """
    raw = state.get("raw_request", "")
    report.raw_request = raw

    if not raw:
        report.cleaned_request = ""
        state["cleaning_notes"] = []
        return ["Empty request — nothing to clean."]

    notes: List[str] = []
    text = raw

    # 1. Unicode NFKC normalisation
    normalised = _normalise_unicode(text)
    if normalised != text:
        notes.append("Applied Unicode NFKC normalisation.")
        text = normalised

    # 2. Quote normalisation
    fixed_quotes = _normalise_quotes(text)
    if fixed_quotes != text:
        notes.append("Normalised smart/curly quotes to straight quotes.")
        text = fixed_quotes

    # 3. Arabic ligature normalisation
    fixed_arabic = _normalise_arabic(text)
    if fixed_arabic != text:
        notes.append("Decomposed Arabic ligatures.")
        text = fixed_arabic

    # 4. Remove invisible characters
    stripped = _remove_invisible(text)
    if stripped != text:
        notes.append("Removed invisible/zero-width characters.")
        text = stripped

    # 5. Whitespace normalisation
    final = _collapse_whitespace(text)
    if final != text:
        notes.append("Normalised whitespace (collapsed runs, trimmed lines).")
        text = final

    report.cleaned_request = text
    state["cleaning_notes"] = notes

    return []


__all__ = ["run"]
