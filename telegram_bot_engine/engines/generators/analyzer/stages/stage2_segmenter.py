"""
Stage 2 — Text segmentation.

Responsibilities:
    * Split the cleaned text into sentences.
    * Split each sentence into words.
    * Produce a flat list of :class:`Token` objects with role and
      confidence information.
    * Detect the request language (Arabic / English / mixed).

Sentence boundaries for Arabic and English are handled.  Arabic
sentences may end with the Arabic full stop (.) or standard punctuation.
English sentences end with ., !, ?.

Tokens are tagged with roles:
    * ``"punctuation"`` — standalone punctuation marks.
    * ``"number"`` — numeric tokens.
    * ``"arabic"`` — Arabic word tokens.
    * ``"english"`` — English word tokens.
    * ``"filler"`` — common filler words (the, a, is, و, في, ...).
"""

from __future__ import annotations

import re
from typing import Dict, List

from ..analysis_report import AnalysisReport, Token


# ---------------------------------------------------------------------------#
# Sentence splitting
# ---------------------------------------------------------------------------#

# Match sentence-ending punctuation: . ! ? ؛ (Arabic semicolon) ۔ (Arabic full stop)
_SENTENCE_END_RE = re.compile(r"[\.!?؟\u060c\u061b\u061f]+")

# Arabic-specific delimiters
_ARABIC_DELIMITERS = ["\u060c", "\u061b", "\u061f", "\u060d"]  # ، ؛ ؟ ـ


def _split_sentences(text: str) -> List[str]:
    """Split text into a list of sentences."""
    # Insert a boundary marker after sentence-ending punctuation
    marked = _SENTENCE_END_RE.sub(lambda m: m.group() + "\x00", text)
    parts = marked.split("\x00")
    sentences = [p.strip() for p in parts if p.strip()]
    return sentences


# ---------------------------------------------------------------------------#
# Word splitting
# ---------------------------------------------------------------------------#

# A word is either a run of Arabic letters, a run of Latin letters, or a
# run of digits.  Punctuation is separated as individual tokens.
_TOKEN_RE = re.compile(
    r"[\u0621-\u064A]+"        # Arabic letters
    r"|[A-Za-z]+"              # Latin letters
    r"|\d+(?:\.\d+)?"          # Numbers (with optional decimal)
    r"|[^\s\w]"                # Single punctuation/symbol
)


def _tokenise(text: str) -> List[str]:
    """Tokenise a string into word/punctuation tokens."""
    return _TOKEN_RE.findall(text)


# ---------------------------------------------------------------------------#
# Filler words
# ---------------------------------------------------------------------------#

_ENGLISH_FILLERS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "at", "by", "for", "with", "from", "into",
    "that", "this", "these", "those", "it", "its", "and", "or", "but",
    "if", "then", "so", "as", "than", "do", "does", "did", "will", "would",
    "can", "could", "should", "shall", "may", "might", "must", "have",
    "has", "had", "i", "we", "you", "they", "he", "she", "my", "our",
    "your", "their", "me", "us", "him", "her", "them",
})

_ARABIC_FILLERS = frozenset({
    "في", "من", "على", "عن", "مع", "هذا", "هذه", "ذلك", "التي", "الذي",
    "الذين", "اللاتي", "كان", "كانت", "يكون", "تكون", "و", "أو", "ثم",
    "بل", "لكن", "إن", "أن", "إلى", "حتى", "قد", "كل", "بعض", "غير",
    "بين", "خلال", "بعد", "قبل", "عند", "لدي", "هو", "هي", "هم", "هن",
    "انا", "أنا", "نحن", "أنت", "أنتم", "ما", "لا", "لم", "لن",
    "هذا", "هذه", "هؤلاء", "كذلك", "كما", "حيث", "التي", "الذي",
})


def _classify_token(raw: str) -> tuple:
    """Return (normalized, role, confidence) for a raw token."""
    # Punctuation
    if re.fullmatch(r"[^\w]", raw):
        return (raw, "punctuation", 1.0)

    # Number
    if re.fullmatch(r"\d+(?:\.\d+)?", raw):
        return (raw, "number", 1.0)

    # Arabic word
    if re.fullmatch(r"[\u0621-\u064A]+", raw):
        norm = raw
        if norm in _ARABIC_FILLERS:
            return (norm, "filler", 0.9)
        return (norm, "arabic", 0.95)

    # English word
    if re.fullmatch(r"[A-Za-z]+", raw):
        lowered = raw.lower()
        if lowered in _ENGLISH_FILLERS:
            return (lowered, "filler", 0.9)
        return (lowered, "english", 0.95)

    # Unknown
    return (raw, "unknown", 0.5)


# ---------------------------------------------------------------------------#
# Language detection
# ---------------------------------------------------------------------------#

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def _detect_language(text: str) -> str:
    """Detect the dominant language: ``"ar"``, ``"en"``, or ``"mixed"``."""
    arabic_count = len(_ARABIC_RE.findall(text))
    latin_count = len(_LATIN_RE.findall(text))

    if arabic_count == 0 and latin_count > 0:
        return "en"
    if latin_count == 0 and arabic_count > 0:
        return "ar"

    if arabic_count > latin_count * 2:
        return "ar"
    if latin_count > arabic_count * 2:
        return "en"
    return "mixed"


# ---------------------------------------------------------------------------#
# Main entry
# ---------------------------------------------------------------------------#

def run(state: Dict, report: AnalysisReport) -> List[str]:
    """Segment the cleaned text into sentences and tokens.

    Writes:
        report.tokens           ← flat list of Token objects.
        state["sentences"]      ← list of sentence strings.
        state["language"]       ← detected language code.
        state["tokens_by_role"] ← dict mapping role → list of token texts.
    """
    text = report.cleaned_request
    if not text:
        state["sentences"] = []
        state["language"] = "unknown"
        state["tokens_by_role"] = {}
        report.tokens = []
        return ["Nothing to segment — cleaned request is empty."]

    warnings: List[str] = []

    # Sentences
    sentences = _split_sentences(text)
    state["sentences"] = sentences

    # Language
    language = _detect_language(text)
    state["language"] = language

    # Tokens
    tokens: List[Token] = []
    role_groups: Dict[str, List[str]] = {}

    for sentence in sentences:
        for raw in _tokenise(sentence):
            norm, role, conf = _classify_token(raw)
            token = Token(text=raw, normalized=norm, role=role, confidence=conf)
            tokens.append(token)
            role_groups.setdefault(role, []).append(norm)

    report.tokens = tokens
    state["tokens_by_role"] = role_groups

    if not tokens:
        warnings.append("No tokens were extracted from the request.")

    return warnings


__all__ = ["run"]
