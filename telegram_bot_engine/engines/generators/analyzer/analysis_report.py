"""
Analysis report data model — the output of the Core Request Analyzer.

The :class:`AnalysisReport` is the *single, authoritative* description of
the user's request.  Every engine that runs after the analyzer must read
this report instead of the raw user message.

This module defines only data classes — no logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Token / keyword level
# ---------------------------------------------------------------------------

@dataclass
class Token:
    """A single token extracted from the request.

    Attributes:
        text: The raw token text.
        normalized: The cleaned, normalised form.
        role: The grammatical/semantic role detected for the token
            (e.g. ``"keyword"``, ``"filler"``, ``"entity"``, ``"verb"``).
        confidence: 0.0–1.0 confidence that the role is correct.
    """

    text: str
    normalized: str
    role: str = "unknown"
    confidence: float = 1.0


@dataclass
class KeywordMatch:
    """A keyword detected in the request.

    Attributes:
        keyword: The matched keyword (e.g. ``"بوت"``, ``"AI"``).
        category: The category the keyword belongs to
            (``"bot_type"``, ``"feature"``, ``"technology"``,
            ``"database"``, ``"runtime"``, ``"framework"``).
        synonyms: Other surface forms that mapped to this keyword.
        position: Approximate word index where it was found.
        confidence: 0.0–1.0 confidence of the match.
    """

    keyword: str
    category: str
    synonyms: List[str] = field(default_factory=list)
    position: int = 0
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Bot type classification
# ---------------------------------------------------------------------------

@dataclass
class BotTypeEntry:
    """A single bot type detected in the request.

    A request may contain multiple bot types; they are ordered by
    priority (highest first).
    """

    type: str
    display_name: str
    priority: int = 0
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Feature level
# ---------------------------------------------------------------------------

@dataclass
class Feature:
    """A single, independent feature extracted from the request.

    Each feature is atomic — it is never a composite of multiple
    features.  If the user describes "warning and mute system" the
    analyzer produces two separate :class:`Feature` objects.

    Attributes:
        name: Machine name (e.g. ``"warning_system"``).
        display_name: Human-readable name (e.g. ``"Warning System"``).
        description: What the feature does, in the user's own words when
            possible.
        keywords: The keywords that triggered this feature.
        confidence: 0.0–1.0 confidence that the feature was correctly
            identified.
        related_entities: Names of entities this feature relates to
            (e.g. ``"users"``, ``"groups"``).
        related_features: Names of other features this one depends on
            or interacts with.
    """

    name: str
    display_name: str
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    confidence: float = 1.0
    related_entities: List[str] = field(default_factory=list)
    related_features: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Technology level
# ---------------------------------------------------------------------------

@dataclass
class Technology:
    """A technology choice extracted from the request.

    Attributes:
        category: ``"language"``, ``"library"``, ``"database"``,
            ``"runtime"``, ``"framework"``, ``"external_api"``.
        name: The technology name (e.g. ``"Python"``, ``"SQLite"``).
        role: The role this technology plays (e.g. ``"primary_storage"``).
        explicit: ``True`` when the user explicitly named it; ``False``
            when it was inferred.
        confidence: 0.0–1.0 confidence.
    """

    category: str
    name: str
    role: str = ""
    explicit: bool = False
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Relationship level
# ---------------------------------------------------------------------------

@dataclass
class Relationship:
    """A relationship between two analysis entities.

    Attributes:
        source: The source entity (feature, technology, or entity name).
        target: The target entity.
        kind: The kind of relationship (``"depends_on"``,
            ``"uses"``, ``"managed_by"``, ``"stored_in"``).
        description: Human-readable description.
    """

    source: str
    target: str
    kind: str
    description: str = ""


# ---------------------------------------------------------------------------
# Conflict level
# ---------------------------------------------------------------------------

@dataclass
class Conflict:
    """A conflict detected in the request.

    Attributes:
        kind: ``"conflicting_choice"``, ``"ambiguous_role"``, etc.
        description: What the conflict is.
        items: The conflicting items.
        severity: ``"error"`` or ``"warning"``.
        resolution_hint: A suggested way to resolve the conflict.
    """

    kind: str
    description: str
    items: List[str] = field(default_factory=list)
    severity: str = "error"
    resolution_hint: str = ""


# ---------------------------------------------------------------------------
# Missing information
# ---------------------------------------------------------------------------

@dataclass
class MissingInfo:
    """A piece of missing information that must be supplied.

    Attributes:
        field: The field that is missing (e.g. ``"bot_name"``).
        question: The question to ask the user.
        options: Suggested options for the answer.
        default: A default value if the user does not answer (may be
            ``None`` when there is no sensible default).
        required: Whether this information is required to proceed.
    """

    field: str
    question: str
    options: List[str] = field(default_factory=list)
    default: Any = None
    required: bool = True


# ---------------------------------------------------------------------------
# Section confidence
# ---------------------------------------------------------------------------

@dataclass
class ConfidenceScore:
    """Confidence score for a single analysis section.

    Attributes:
        section: The section name (``"bot_type"``, ``"features"``, etc.).
        score: 0.0–1.0 confidence.
        reason: Why the score is what it is.
    """

    section: str
    score: float
    reason: str = ""


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------

@dataclass
class AnalysisReport:
    """The complete, authoritative analysis of a user request.

    This is the **only** object downstream engines should read.  It
    captures everything the analyzer understood about the request.

    Attributes:
        raw_request: The original, unmodified user request.
        cleaned_request: The request after Stage 1 cleaning.
        project_name: Suggested project name.
        bot_types: Ordered list of detected bot types (highest priority
            first).
        description: A full description of what the bot should do.
        features: The list of independent features.
        technologies: The list of detected technologies.
        relationships: The relationships between features and entities.
        conflicts: Detected conflicts.
        missing_info: Missing information that needs answering.
        keywords: All keywords found in the request.
        tokens: The segmented tokens.
        confidence: Per-section confidence scores.
        notes: General notes from the analyzer.
        warnings: Warnings the caller should be aware of.
        questions: The list of questions to ask the user.
        ready: ``True`` when the analysis is complete enough to proceed.
    """

    raw_request: str = ""
    cleaned_request: str = ""
    project_name: str = ""
    bot_types: List[BotTypeEntry] = field(default_factory=list)
    description: str = ""
    features: List[Feature] = field(default_factory=list)
    technologies: List[Technology] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    missing_info: List[MissingInfo] = field(default_factory=list)
    keywords: List[KeywordMatch] = field(default_factory=list)
    tokens: List[Token] = field(default_factory=list)
    confidence: List[ConfidenceScore] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    ready: bool = False

    # -- convenience -------------------------------------------------------

    @property
    def primary_bot_type(self) -> Optional[BotTypeEntry]:
        """Return the highest-priority bot type, or ``None``."""
        if self.bot_types:
            return self.bot_types[0]
        return None

    @property
    def feature_names(self) -> List[str]:
        return [f.name for f in self.features]

    @property
    def has_conflicts(self) -> bool:
        return any(c.severity == "error" for c in self.conflicts)

    @property
    def has_missing_required_info(self) -> bool:
        return any(m.required for m in self.missing_info)

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation suitable for serialisation."""
        import dataclasses
        return dataclasses.asdict(self)


__all__ = [
    "Token",
    "KeywordMatch",
    "BotTypeEntry",
    "Feature",
    "Technology",
    "Relationship",
    "Conflict",
    "MissingInfo",
    "ConfidenceScore",
    "AnalysisReport",
]
