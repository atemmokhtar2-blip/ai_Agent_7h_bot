"""
Stage 7 — Relationship analysis.

Responsibilities:
    * Analyse relationships between features, technologies, and entities.
    * Produce a list of :class:`Relationship` objects describing how
      components depend on, use, or manage each other.
    * Relationship kinds: ``"depends_on"``, ``"uses"``,
      ``"managed_by"``, ``"stored_in"``, ``"provides"``.

Relationships are derived from:
    * Feature → feature relations (from Stage 5's related_features).
    * Feature → technology relations (e.g. database feature uses SQLite).
    * Bot type → feature relations (e.g. store bot provides payments).
    * Feature → entity relations (e.g. user_management manages users).
"""

from __future__ import annotations

from typing import Dict, List

from ..analysis_report import AnalysisReport, Relationship


# ---------------------------------------------------------------------------#
# Bot type → feature provision map
# ---------------------------------------------------------------------------#

_BOT_TYPE_FEATURES: Dict[str, List[str]] = {
    "store": ["shopping_cart", "product_catalog", "order_management",
              "payments", "database", "admin_panel"],
    "group_admin": ["welcome", "ban", "user_management", "logging",
                    "admin_panel", "notifications"],
    "downloader": ["media_download", "file_upload", "search"],
    "ai_assistant": ["ai_chat", "database"],
    "task_manager": ["database", "notifications", "scheduling"],
    "quiz": ["database"],
    "news": ["subscription", "notifications", "database"],
    "weather": ["search"],
    "currency": ["search", "database"],
    "assistant": ["search"],
    "general": [],
}


# Feature → entity management
_FEATURE_ENTITIES: Dict[str, List[str]] = {
    "user_management": ["users"],
    "admin_panel": ["users"],
    "welcome": ["users"],
    "ban": ["users", "groups"],
    "authentication": ["users"],
    "rate_limit": ["users"],
    "notifications": ["users"],
    "subscription": ["users"],
    "shopping_cart": ["products", "orders"],
    "product_catalog": ["products"],
    "order_management": ["orders"],
    "payments": ["orders", "transactions"],
    "content_management": ["content"],
    "analytics": ["events"],
}


# Feature → database storage
_FEATURES_NEEDING_DB: List[str] = [
    "database", "user_management", "admin_panel", "order_management",
    "shopping_cart", "product_catalog", "payments", "subscription",
    "analytics", "logging", "ban", "welcome", "ai_chat", "scheduling",
]


def run(state: Dict, report: AnalysisReport) -> List[str]:
    """Analyse relationships between analysis entities.

    Writes:
        report.relationships ← list of Relationship objects.
    """
    warnings: List[str] = []

    relationships: List[Relationship] = []
    feature_names: set = state.get("feature_names", set())
    bot_type: str = state.get("primary_bot_type", "general")

    # 1. Bot type provides features
    type_features = _BOT_TYPE_FEATURES.get(bot_type, [])
    for feat_name in type_features:
        if feat_name in feature_names:
            relationships.append(Relationship(
                source=bot_type,
                target=feat_name,
                kind="provides",
                description=f"The {bot_type} bot type provides the {feat_name} feature.",
            ))

    # 2. Feature → feature dependencies (from Stage 5)
    for feat in report.features:
        for related in feat.related_features:
            if related in feature_names:
                relationships.append(Relationship(
                    source=feat.name,
                    target=related,
                    kind="depends_on",
                    description=f"Feature '{feat.name}' depends on '{related}'.",
                ))

    # 3. Feature → entity management
    for feat in report.features:
        entities = _FEATURE_ENTITIES.get(feat.name, [])
        for entity in entities:
            relationships.append(Relationship(
                source=feat.name,
                target=entity,
                kind="managed_by",
                description=f"Feature '{feat.name}' manages entity '{entity}'.",
            ))

    # 4. Features → database (stored_in)
    db_techs = [
        t for t in report.technologies if t.category == "database"
    ]
    if db_techs:
        db_name = db_techs[0].name
        for feat in report.features:
            if feat.name in _FEATURES_NEEDING_DB:
                relationships.append(Relationship(
                    source=feat.name,
                    target=db_name,
                    kind="stored_in",
                    description=f"Feature '{feat.name}' stores data in {db_name}.",
                ))

    # 5. Feature → technology (uses)
    for feat in report.features:
        for tech in report.technologies:
            if tech.category == "library":
                # Check if this feature uses this library
                if (feat.name == "media_download" and "yt-dlp" in tech.name.lower()) or \
                   (feat.name == "file_upload" and "requests" in tech.name.lower()) or \
                   (feat.name == "ai_chat" and "openai" in tech.name.lower()):
                    relationships.append(Relationship(
                        source=feat.name,
                        target=tech.name,
                        kind="uses",
                        description=f"Feature '{feat.name}' uses {tech.name}.",
                    ))

    # 6. Bot type → technology (uses)
    for tech in report.technologies:
        if tech.category == "framework":
            relationships.append(Relationship(
                source=bot_type,
                target=tech.name,
                kind="uses",
                description=f"The {bot_type} bot uses the {tech.name} framework.",
            ))
        if tech.category == "language":
            relationships.append(Relationship(
                source=bot_type,
                target=tech.name,
                kind="uses",
                description=f"The {bot_type} bot is implemented in {tech.name}.",
            ))

    # Deduplicate by (source, target, kind)
    seen = set()
    unique: List[Relationship] = []
    for rel in relationships:
        key = (rel.source, rel.target, rel.kind)
        if key not in seen:
            seen.add(key)
            unique.append(rel)

    report.relationships = unique

    if not report.relationships:
        warnings.append("No relationships were detected in the request.")

    return warnings


__all__ = ["run"]
