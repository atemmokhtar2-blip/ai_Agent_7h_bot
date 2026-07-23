"""
Stage 10 — Final analysis report assembly.

Responsibilities:
    * Assemble the final :class:`AnalysisReport` from all previous stages.
    * Compute per-section confidence scores.
    * Generate the project description.
    * Generate the project name (if not explicitly provided).
    * Determine the ``ready`` flag — whether the analysis is complete
      enough to proceed to downstream engines.
    * Collect all notes and warnings from previous stages.

This stage does **not** add new analysis — it only assembles what the
previous stages produced.
"""

from __future__ import annotations

from typing import Dict, List

from ..analysis_report import AnalysisReport, ConfidenceScore


# ---------------------------------------------------------------------------#
# Project name generation
# ---------------------------------------------------------------------------#

# Arabic → English keyword mapping for slug generation
_AR_EN_MAP: Dict[str, str] = {
    "متجر": "store", "متجري": "store",
    "ادارة": "admin", "إدارة": "admin", "اداره": "admin",
    "مدير": "admin", "مشرف": "moderator",
    "تخكيم": "admin",
    "تحميل": "downloader", "تنزيل": "downloader",
    "يوتيوب": "youtube",
    "ذكاء": "ai", "اصطناعي": "ai",
    "مساعد": "assistant",
    "بوت": "bot", "روبوت": "bot",
    "تيليجرام": "telegram", "تيليغرام": "telegram",
    "مهمة": "task", "مهام": "tasks",
    "اخبار": "news", "أخبار": "news",
    "طقس": "weather",
    "اسعار": "currency", "أسعار": "currency",
    "محادثة": "chat", "دردشة": "chat",
    "فيديو": "video",
    "دفع": "payment", "مدفوعات": "payments",
    "قاعدة": "database", "بيانات": "data",
    "لوحة": "panel", "تحكم": "control",
    "مستخدم": "user", "مستخدمين": "users",
    "اشتراك": "subscription",
    "سلة": "cart", "مشتريات": "shopping",
    "منتجات": "products", "منتج": "product",
    "طلب": "order", "طلبات": "orders",
}


def _slugify_bot_type(bot_type: str) -> str:
    """Convert a bot type to a readable project name."""
    parts = bot_type.split("_")
    return "_".join(parts) + "_bot"


def _generate_project_name(state: Dict, report: AnalysisReport) -> str:
    """Generate a project name from the bot type and features."""
    bot_type = state.get("primary_bot_type", "general")

    # Use Arabic→English mapping to build a meaningful name
    # Look for Arabic tokens that map to English words
    arabic_tokens = state.get("tokens_by_role", {}).get("arabic", [])
    en_parts: List[str] = []
    for token in arabic_tokens:
        if token in _AR_EN_MAP:
            mapped = _AR_EN_MAP[token]
            if mapped not in en_parts:
                en_parts.append(mapped)

    if en_parts:
        return "_".join(en_parts) + "_bot"

    return _slugify_bot_type(bot_type)


# ---------------------------------------------------------------------------#
# Description generation
# ---------------------------------------------------------------------------#

def _generate_description(state: Dict, report: AnalysisReport) -> str:
    """Generate a human-readable description from the analysis."""
    bot_type = state.get("primary_bot_type", "general")
    primary = report.primary_bot_type

    parts: List[str] = []

    if primary:
        parts.append(f"A {primary.display_name.lower()}.")

    if report.features:
        feature_list = [f.display_name for f in report.features]
        if len(feature_list) == 1:
            parts.append(f"It includes: {feature_list[0]}.")
        else:
            parts.append(
                f"It includes: {', '.join(feature_list[:-1])}, "
                f"and {feature_list[-1]}."
            )

    if report.technologies:
        tech_list = [t.name for t in report.technologies]
        if len(tech_list) == 1:
            parts.append(f"Built with {tech_list[0]}.")
        else:
            parts.append(
                f"Built with {', '.join(tech_list[:-1])}, "
                f"and {tech_list[-1]}."
            )

    return " ".join(parts) if parts else "A Telegram bot."


# ---------------------------------------------------------------------------#
# Confidence scoring
# ---------------------------------------------------------------------------#

def _compute_confidence(state: Dict, report: AnalysisReport) -> List[ConfidenceScore]:
    """Compute per-section confidence scores."""
    scores: List[ConfidenceScore] = []

    # Bot type confidence
    if report.bot_types:
        primary = report.bot_types[0]
        scores.append(ConfidenceScore(
            section="bot_type",
            score=primary.confidence,
            reason=(
                f"Primary type '{primary.type}' with confidence "
                f"{primary.confidence:.2f} based on "
                f"{len(primary.evidence)} evidence item(s)."
            ),
        ))
    else:
        scores.append(ConfidenceScore(
            section="bot_type",
            score=0.3,
            reason="No bot type was detected.",
        ))

    # Feature confidence
    if report.features:
        avg = sum(f.confidence for f in report.features) / len(report.features)
        scores.append(ConfidenceScore(
            section="features",
            score=round(avg, 3),
            reason=f"{len(report.features)} feature(s) detected with average confidence {avg:.2f}.",
        ))
    else:
        scores.append(ConfidenceScore(
            section="features",
            score=0.2,
            reason="No features were detected.",
        ))

    # Technology confidence
    if report.technologies:
        explicit_count = sum(1 for t in report.technologies if t.explicit)
        total = len(report.technologies)
        ratio = explicit_count / total if total > 0 else 0
        scores.append(ConfidenceScore(
            section="technologies",
            score=round(ratio, 3),
            reason=f"{explicit_count}/{total} technologies were explicitly mentioned.",
        ))
    else:
        scores.append(ConfidenceScore(
            section="technologies",
            score=0.3,
            reason="No technologies detected; defaults will be used.",
        ))

    # Keyword confidence
    if report.keywords:
        avg = sum(k.confidence for k in report.keywords) / len(report.keywords)
        scores.append(ConfidenceScore(
            section="keywords",
            score=round(avg, 3),
            reason=f"{len(report.keywords)} keyword(s) matched with average confidence {avg:.2f}.",
        ))
    else:
        scores.append(ConfidenceScore(
            section="keywords",
            score=0.1,
            reason="No keywords were matched.",
        ))

    # Overall confidence
    section_scores = [s.score for s in scores]
    overall = sum(section_scores) / len(section_scores) if section_scores else 0
    scores.append(ConfidenceScore(
        section="overall",
        score=round(overall, 3),
        reason=f"Average of all section confidence scores.",
    ))

    return scores


# ---------------------------------------------------------------------------#
# Main entry
# ---------------------------------------------------------------------------#

def run(state: Dict, report: AnalysisReport) -> List[str]:
    """Assemble the final analysis report.

    Writes:
        report.project_name  ← generated project name.
        report.description   ← generated description.
        report.confidence    ← per-section confidence scores.
        report.notes         ← all notes from previous stages.
        report.ready         ← whether the analysis is ready for downstream.
    """
    warnings: List[str] = []

    # Project name
    report.project_name = _generate_project_name(state, report)

    # Description
    report.description = _generate_description(state, report)

    # Confidence scores
    report.confidence = _compute_confidence(state, report)

    # Notes from cleaning stage
    report.notes = list(state.get("cleaning_notes", []))

    # Determine readiness
    has_errors = report.has_conflicts
    has_required_missing = report.has_missing_required_info

    if has_errors:
        report.ready = False
        warnings.append(
            "Analysis is NOT ready — there are error-level conflicts that "
            "must be resolved before proceeding."
        )
    elif has_required_missing:
        report.ready = False
        warnings.append(
            "Analysis is NOT ready — there is missing required information."
        )
    else:
        report.ready = True

    # Add a note about readiness
    if report.ready:
        report.notes.append("Analysis complete and ready for downstream engines.")
    else:
        report.notes.append(
            "Analysis incomplete — resolve conflicts and/or answer "
            "missing information questions before proceeding."
        )

    return warnings


__all__ = ["run"]
