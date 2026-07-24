"""
Intent analyzer — performs the Intent Analysis.

The :class:`IntentAnalyzer` is responsible for understanding the
user's intent across five dimensions:

* **wants** — what the user wants (the desired outcome).
* **does_not_want** — what the user explicitly does not want
  (constraints, exclusions, anti-requirements).
* **final_goal** — the ultimate goal the user is trying to achieve.
* **constraints** — the limitations and boundaries within which the
  solution must operate.
* **quality_level** — the level of quality the user expects (minimal,
  standard, high, or production).

The analyzer reads the :class:`RequestData`, :class:`ContextData`,
:class:`GraphData`, and :class:`KnowledgeData` and produces an
:class:`IntentAnalysis`.

The analyzer does **not** write code, create files, or make build
decisions.  It only *understands* the intent.
"""

from __future__ import annotations

import re
from typing import List

from .context_reader import ContextData
from .graph_reader import GraphData
from .knowledge_reader import KnowledgeData
from .report_data import (
    IntentAnalysis,
    IntentDimension,
    QUALITY_LEVEL_HIGH,
    QUALITY_LEVEL_MINIMAL,
    QUALITY_LEVEL_PRODUCTION,
    QUALITY_LEVEL_STANDARD,
    SOURCE_KNOWLEDGE_BASE,
    SOURCE_PROJECT_CONTEXT,
    SOURCE_USER_REQUEST,
)
from .request_reader import RequestData


# ---------------------------------------------------------------------------#
# Negation / exclusion patterns
# ---------------------------------------------------------------------------#
#
# Patterns that indicate the user does NOT want something.  These are
# matched case-insensitively against the request.  The first group
# captures the thing the user does not want.

_NEGATION_PATTERNS = [
    re.compile(r"(?:without|no|not|don't|never|avoid|skip)\s+(.+)", re.I),
    re.compile(r"(?:بدون|لا|من\s+غير|تجنب|لا\s+تستخدم)\s+(.+)", re.I),
]

# Patterns that indicate a quality level.
_QUALITY_KEYWORDS = {
    QUALITY_LEVEL_PRODUCTION: [
        "production", "enterprise", "scalable", "high availability",
        "ha", "industrial", "إنتاج", "إنتاجي", "مؤسسي",
    ],
    QUALITY_LEVEL_HIGH: [
        "high quality", "robust", "comprehensive", "professional",
        "جودة عالية", "احترافي", "متكامل",
    ],
    QUALITY_LEVEL_STANDARD: [
        "standard", "normal", "typical", "regular", "عادي", "قياسي",
    ],
    QUALITY_LEVEL_MINIMAL: [
        "minimal", "simple", "basic", "mvp", "prototype", "بسيط",
        "أساسي", "مبدئي",
    ],
}

# Patterns that indicate a constraint.
_CONSTRAINT_KEYWORDS = [
    "must", "have to", "need to", "required", "only", "limit",
    "maximum", "minimum", "at most", "at least", "within",
    "يجب", "لازم", "مطلوب", "الحد", "الأقصى", "الأدنى",
]


class IntentAnalyzer:
    """Performs the Intent Analysis across the five dimensions.

    The analyzer is the component that *understands* the user's
    intent.  It reads the four data sources and produces an
    :class:`IntentAnalysis` that captures the five dimensions.

    The analyzer is rule-based and heuristic.  In a future phase it
    can be replaced with an LLM-backed implementation without
    affecting any other component.
    """

    def analyze(
        self,
        request: RequestData,
        context: ContextData,
        graph: GraphData,
        knowledge: KnowledgeData,
    ) -> IntentAnalysis:
        """Analyze the intent and return an :class:`IntentAnalysis`."""
        text = request.cleaned_request or request.raw_request

        wants = self._extract_wants(text, request, context)
        does_not_want = self._extract_does_not_want(text)
        final_goal = self._extract_final_goal(
            text, request, context,
        )
        constraints = self._extract_constraints(
            text, context, knowledge,
        )
        quality_level = self._extract_quality_level(
            text, knowledge,
        )

        dimensions: List[IntentDimension] = []
        dimensions.append(IntentDimension(
            name="wants",
            value=wants,
            confidence=0.9 if wants else 0.5,
            evidence=self._wants_evidence(request, context),
            source_artefact=SOURCE_USER_REQUEST,
        ))
        dimensions.append(IntentDimension(
            name="does_not_want",
            value=does_not_want,
            confidence=0.8 if does_not_want else 0.5,
            evidence=self._does_not_want_evidence(text),
            source_artefact=SOURCE_USER_REQUEST,
        ))
        dimensions.append(IntentDimension(
            name="final_goal",
            value=final_goal,
            confidence=0.85 if final_goal else 0.5,
            evidence=self._final_goal_evidence(request, context),
            source_artefact=(
                SOURCE_PROJECT_CONTEXT if context.available
                else SOURCE_USER_REQUEST
            ),
        ))
        dimensions.append(IntentDimension(
            name="constraints",
            value=constraints,
            confidence=0.8 if constraints else 0.5,
            evidence=self._constraints_evidence(text, knowledge),
            source_artefact=SOURCE_USER_REQUEST,
        ))
        dimensions.append(IntentDimension(
            name="quality_level",
            value=quality_level,
            confidence=0.7,
            evidence=self._quality_evidence(text),
            source_artefact=(
                SOURCE_KNOWLEDGE_BASE if not knowledge.available
                else SOURCE_USER_REQUEST
            ),
        ))

        overall_confidence = (
            sum(d.confidence for d in dimensions) / len(dimensions)
            if dimensions else 0.5
        )

        return IntentAnalysis(
            wants=wants,
            does_not_want=does_not_want,
            final_goal=final_goal,
            constraints=constraints,
            quality_level=quality_level,
            dimensions=dimensions,
            confidence=round(overall_confidence, 3),
        )

    # ----------------------------------------------------------------- #
    # Wants
    # ----------------------------------------------------------------- #

    def _extract_wants(
        self,
        text: str,
        request: RequestData,
        context: ContextData,
    ) -> str:
        """Extract what the user wants."""
        # Prefer the analysis report's description.
        if request.description:
            return request.description
        # Fall back to the primary goal from the project context.
        if context.available and context.primary_goal:
            return context.primary_goal
        # Fall back to the cleaned request.
        if text:
            # Truncate to a reasonable length.
            return text[:500]
        return ""

    def _wants_evidence(
        self,
        request: RequestData,
        context: ContextData,
    ) -> List[str]:
        evidence: List[str] = []
        if request.description:
            evidence.append("analysis_report.description")
        if request.features:
            evidence.append(f"features: {', '.join(request.features[:5])}")
        if request.bot_types:
            evidence.append(f"bot_types: {', '.join(request.bot_types)}")
        if context.available:
            evidence.append("project_context.goal")
        return evidence

    # ----------------------------------------------------------------- #
    # Does not want
    # ----------------------------------------------------------------- #

    def _extract_does_not_want(self, text: str) -> str:
        """Extract what the user does not want."""
        if not text:
            return ""
        matches: List[str] = []
        for pattern in _NEGATION_PATTERNS:
            for match in pattern.finditer(text):
                captured = match.group(1).strip()
                # Truncate long captures.
                if len(captured) > 100:
                    captured = captured[:100] + "..."
                if captured:
                    matches.append(captured)
        if not matches:
            return ""
        # Deduplicate while preserving order.
        seen: set = set()
        unique: List[str] = []
        for m in matches:
            key = m.lower()
            if key not in seen:
                seen.add(key)
                unique.append(m)
        return "; ".join(unique[:5])

    def _does_not_want_evidence(self, text: str) -> List[str]:
        evidence: List[str] = []
        for pattern in _NEGATION_PATTERNS:
            for match in pattern.finditer(text):
                evidence.append(f"negation pattern: '{match.group(0)}'")
        return evidence[:5]

    # ----------------------------------------------------------------- #
    # Final goal
    # ----------------------------------------------------------------- #

    def _extract_final_goal(
        self,
        text: str,
        request: RequestData,
        context: ContextData,
    ) -> str:
        """Extract the ultimate goal the user is trying to achieve."""
        # Prefer the project context's primary goal.
        if context.available and context.primary_goal:
            return context.primary_goal
        # Fall back to the analysis report's description.
        if request.description:
            return request.description
        # Fall back to the cleaned request (first sentence).
        if text:
            sentences = re.split(r"[.!?]\s+", text)
            if sentences:
                return sentences[0].strip()[:200]
        return ""

    def _final_goal_evidence(
        self,
        request: RequestData,
        context: ContextData,
    ) -> List[str]:
        evidence: List[str] = []
        if context.available:
            evidence.append("project_context.goal.primary_goal")
        if request.description:
            evidence.append("analysis_report.description")
        return evidence

    # ----------------------------------------------------------------- #
    # Constraints
    # ----------------------------------------------------------------- #

    def _extract_constraints(
        self,
        text: str,
        context: ContextData,
        knowledge: KnowledgeData,
    ) -> str:
        """Extract the constraints and boundaries."""
        constraints: List[str] = []

        # From the request text.
        if text:
            lowered = text.lower()
            for kw in _CONSTRAINT_KEYWORDS:
                if kw in lowered:
                    # Find the sentence containing the keyword.
                    sentences = re.split(r"[.!?;\n]+", text)
                    for sentence in sentences:
                        if kw.lower() in sentence.lower():
                            cleaned = sentence.strip()
                            if cleaned and len(cleaned) > 3:
                                if len(cleaned) > 120:
                                    cleaned = cleaned[:120] + "..."
                                constraints.append(cleaned)
                                break

        # From the knowledge base.
        if knowledge.available:
            constraints.extend(knowledge.constraints[:3])

        if not constraints:
            return ""

        # Deduplicate.
        seen: set = set()
        unique: List[str] = []
        for c in constraints:
            key = c.lower()
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return "; ".join(unique[:5])

    def _constraints_evidence(
        self,
        text: str,
        knowledge: KnowledgeData,
    ) -> List[str]:
        evidence: List[str] = []
        if text:
            lowered = text.lower()
            matched = [kw for kw in _CONSTRAINT_KEYWORDS if kw in lowered]
            if matched:
                evidence.append(f"constraint keywords: {', '.join(matched)}")
        if knowledge.available and knowledge.constraints:
            evidence.append("knowledge_base.constraints")
        return evidence

    # ----------------------------------------------------------------- #
    # Quality level
    # ----------------------------------------------------------------- #

    def _extract_quality_level(
        self,
        text: str,
        knowledge: KnowledgeData,
    ) -> str:
        """Extract the quality level the user expects."""
        if text:
            lowered = text.lower()
            # Check from highest to lowest.
            for level in (
                QUALITY_LEVEL_PRODUCTION,
                QUALITY_LEVEL_HIGH,
                QUALITY_LEVEL_STANDARD,
                QUALITY_LEVEL_MINIMAL,
            ):
                for kw in _QUALITY_KEYWORDS.get(level, []):
                    if kw in lowered:
                        return level

        # Check the knowledge base for a default quality level.
        if knowledge.available:
            kb_level = knowledge.get("quality_level")
            if isinstance(kb_level, str) and kb_level:
                return kb_level
            default_level = knowledge.defaults.get("quality_level")
            if isinstance(default_level, str) and default_level:
                return default_level

        return QUALITY_LEVEL_STANDARD

    def _quality_evidence(self, text: str) -> List[str]:
        evidence: List[str] = []
        if text:
            lowered = text.lower()
            for level, keywords in _QUALITY_KEYWORDS.items():
                matched = [kw for kw in keywords if kw in lowered]
                if matched:
                    evidence.append(
                        f"quality '{level}': {', '.join(matched)}",
                    )
        return evidence


__all__ = ["IntentAnalyzer"]
