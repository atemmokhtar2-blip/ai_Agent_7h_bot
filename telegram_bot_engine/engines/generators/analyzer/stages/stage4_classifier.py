"""
Stage 4 — Request classification.

Responsibilities:
    * Determine which bot type(s) the request describes.
    * Produce an ordered list of :class:`BotTypeEntry` objects (highest
      priority first).
    * Score each bot type with confidence and supporting evidence.
    * Assign priorities — the dominant type gets the highest priority.

A request may indicate multiple bot types (e.g. "store bot with admin
panel" → store + admin).  Each detected type gets its own entry, ordered
by priority.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..analysis_report import AnalysisReport, BotTypeEntry


# ---------------------------------------------------------------------------#
# Bot type metadata
# ---------------------------------------------------------------------------#

_BOT_TYPE_DISPLAY: Dict[str, str] = {
    "store": "E-commerce / Store Bot",
    "group_admin": "Group Administration Bot",
    "downloader": "Media Downloader Bot",
    "ai_assistant": "AI Assistant Bot",
    "task_manager": "Task Management Bot",
    "quiz": "Quiz / Poll Bot",
    "news": "News Bot",
    "weather": "Weather Bot",
    "currency": "Currency / Price Bot",
    "assistant": "General Assistant Bot",
    "general": "General Purpose Bot",
}

# Keywords that, when present, indicate each bot type.
# These map keyword canonicals (from Stage 3) to bot types.
_TYPE_KEYWORD_MAP: Dict[str, str] = {
    "store": "store",
    "group_admin": "group_admin",
    "downloader": "downloader",
    "media_download": "downloader",
    "ai_assistant": "ai_assistant",
    "ai_chat": "ai_assistant",
    "task_manager": "task_manager",
    "quiz": "quiz",
    "news": "news",
    "weather": "weather",
    "currency": "currency",
    "shopping_cart": "store",
    "product_catalog": "store",
    "order_management": "store",
    "user_management": "group_admin",
    "ban": "group_admin",
    "welcome": "group_admin",
}

# Secondary indicators — features that suggest a bot type with lower
# confidence.
_SECONDARY_INDICATORS: Dict[str, str] = {
    "payments": "store",
    "admin_panel": "group_admin",
    "subscription": "news",
    "analytics": "general",
}


# ---------------------------------------------------------------------------#
# Classification logic
# ---------------------------------------------------------------------------#

def run(state: Dict, report: AnalysisReport) -> List[str]:
    """Classify the request into one or more bot types.

    Writes:
        report.bot_types ← ordered list of BotTypeEntry (highest priority
                           first).
        state["primary_bot_type"] ← the top type string.
    """
    warnings: List[str] = []

    keyword_canonicals: set = state.get("keyword_canonicals", set())
    keywords = report.keywords

    # Build a map: canonical → KeywordMatch (for evidence)
    kw_by_name = {kw.keyword: kw for kw in keywords}

    # Score each candidate type
    type_scores: Dict[str, float] = {}
    type_evidence: Dict[str, List[str]] = {}

    for canonical, bot_type in _TYPE_KEYWORD_MAP.items():
        if canonical in keyword_canonicals:
            kw = kw_by_name[canonical]
            type_scores[bot_type] = type_scores.get(bot_type, 0) + kw.confidence
            evidence = type_evidence.setdefault(bot_type, [])
            evidence.append(f"keyword '{canonical}' (conf={kw.confidence:.2f})")

    for canonical, bot_type in _SECONDARY_INDICATORS.items():
        if canonical in keyword_canonicals:
            kw = kw_by_name[canonical]
            type_scores[bot_type] = type_scores.get(bot_type, 0) + kw.confidence * 0.5
            evidence = type_evidence.setdefault(bot_type, [])
            evidence.append(f"secondary '{canonical}' (conf={kw.confidence:.2f})")

    # If no type was detected, fall back to "general"
    if not type_scores:
        report.bot_types = [BotTypeEntry(
            type="general",
            display_name=_BOT_TYPE_DISPLAY.get("general", "General Purpose Bot"),
            priority=0,
            confidence=0.5,
            evidence=["No specific bot-type keywords detected; defaulting to general."],
        )]
        state["primary_bot_type"] = "general"
        warnings.append(
            "No specific bot type detected — defaulting to 'general'."
        )
        return warnings

    # Build entries, sorted by score descending
    entries: List[BotTypeEntry] = []
    sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)

    for priority_idx, (bot_type, score) in enumerate(sorted_types):
        # Normalise score to 0–1 (max possible is sum of all keyword confidences)
        max_possible = sum(
            kw.confidence for kw in keywords
            if _TYPE_KEYWORD_MAP.get(kw.keyword) == bot_type
            or _SECONDARY_INDICATORS.get(kw.keyword) == bot_type
        )
        if max_possible > 0:
            confidence = min(score / max_possible if max_possible > 1 else score, 1.0)
        else:
            confidence = score

        entries.append(BotTypeEntry(
            type=bot_type,
            display_name=_BOT_TYPE_DISPLAY.get(
                bot_type, bot_type.replace("_", " ").title()
            ),
            priority=len(sorted_types) - priority_idx,
            confidence=round(confidence, 3),
            evidence=type_evidence.get(bot_type, []),
        ))

    report.bot_types = entries
    state["primary_bot_type"] = entries[0].type

    return warnings


__all__ = ["run"]
