"""
Stage 6 — Technology extraction.

Responsibilities:
    * Identify technologies mentioned or implied by the request.
    * Produce a list of :class:`Technology` objects with category, name,
      role, explicit flag, and confidence.
    * Categories: ``"language"``, ``"library"``, ``"database"``,
      ``"runtime"``, ``"framework"``, ``"external_api"``.

Technologies can be:
    * **Explicit** — the user named them (e.g. "use PostgreSQL", "with
      Docker").
    * **Inferred** — implied by the features/bot type (e.g. a downloader
      bot implies yt-dlp; a store bot implies a database).
"""

from __future__ import annotations

from typing import Dict, List, Set

from ..analysis_report import AnalysisReport, Technology


# ---------------------------------------------------------------------------#
# Technology keyword → Technology mapping
# ---------------------------------------------------------------------------#

_TECH_KEYWORD_MAP: Dict[str, Technology] = {}

# Language
_TECH_KEYWORD_MAP["python"] = Technology(
    category="language", name="Python", role="primary_language",
    explicit=True, confidence=1.0,
)
_TECH_KEYWORD_MAP["nodejs"] = Technology(
    category="language", name="Node.js", role="primary_language",
    explicit=True, confidence=0.9,
)

# Databases
_TECH_KEYWORD_MAP["sqlite"] = Technology(
    category="database", name="SQLite", role="data_storage",
    explicit=True, confidence=0.95,
)
_TECH_KEYWORD_MAP["postgres"] = Technology(
    category="database", name="PostgreSQL", role="data_storage",
    explicit=True, confidence=0.95,
)
_TECH_KEYWORD_MAP["mysql"] = Technology(
    category="database", name="MySQL", role="data_storage",
    explicit=True, confidence=0.9,
)
_TECH_KEYWORD_MAP["mongodb"] = Technology(
    category="database", name="MongoDB", role="data_storage",
    explicit=True, confidence=0.9,
)
_TECH_KEYWORD_MAP["redis"] = Technology(
    category="database", name="Redis", role="cache_storage",
    explicit=True, confidence=0.9,
)

# Frameworks
_TECH_KEYWORD_MAP["python_telegram_bot"] = Technology(
    category="framework", name="python-telegram-bot", role="telegram_api",
    explicit=True, confidence=0.9,
)
_TECH_KEYWORD_MAP["aiogram"] = Technology(
    category="framework", name="aiogram", role="telegram_api",
    explicit=True, confidence=0.9,
)
_TECH_KEYWORD_MAP["pyrogram"] = Technology(
    category="framework", name="pyrogram", role="telegram_api",
    explicit=True, confidence=0.9,
)
_TECH_KEYWORD_MAP["telethon"] = Technology(
    category="framework", name="telethon", role="telegram_api",
    explicit=True, confidence=0.9,
)
_TECH_KEYWORD_MAP["flask"] = Technology(
    category="framework", name="Flask", role="web_framework",
    explicit=True, confidence=0.85,
)
_TECH_KEYWORD_MAP["fastapi"] = Technology(
    category="framework", name="FastAPI", role="web_framework",
    explicit=True, confidence=0.85,
)

# Libraries
_TECH_KEYWORD_MAP["requests"] = Technology(
    category="library", name="requests/httpx", role="http_client",
    explicit=True, confidence=0.85,
)
_TECH_KEYWORD_MAP["sqlalchemy"] = Technology(
    category="library", name="SQLAlchemy", role="orm",
    explicit=True, confidence=0.85,
)
_TECH_KEYWORD_MAP["pillow"] = Technology(
    category="library", name="Pillow (PIL)", role="image_processing",
    explicit=True, confidence=0.8,
)
_TECH_KEYWORD_MAP["yt-dlp"] = Technology(
    category="library", name="yt-dlp", role="media_downloader",
    explicit=True, confidence=0.9,
)
_TECH_KEYWORD_MAP["ffmpeg"] = Technology(
    category="library", name="FFmpeg", role="media_processing",
    explicit=True, confidence=0.85,
)

# Runtime
_TECH_KEYWORD_MAP["docker"] = Technology(
    category="runtime", name="Docker", role="containerisation",
    explicit=True, confidence=0.9,
)

# External APIs
_TECH_KEYWORD_MAP["openai"] = Technology(
    category="external_api", name="OpenAI API", role="ai_provider",
    explicit=True, confidence=0.9,
)


# ---------------------------------------------------------------------------#
# Inferred technologies — implied by features/bot type
# ---------------------------------------------------------------------------#

def _infer_technologies(
    bot_type: str,
    feature_names: Set[str],
    keyword_canonicals: Set[str],
) -> List[Technology]:
    """Infer technologies that are not explicitly mentioned."""
    inferred: List[Technology] = []

    # Python is always inferred (the engine generates Python bots)
    if "python" not in keyword_canonicals:
        inferred.append(Technology(
            category="language", name="Python", role="primary_language",
            explicit=False, confidence=0.8,
        ))

    # python-telegram-bot is the default framework
    if not any(k in keyword_canonicals for k in (
        "python_telegram_bot", "aiogram", "pyrogram", "telethon",
    )):
        inferred.append(Technology(
            category="framework", name="python-telegram-bot",
            role="telegram_api", explicit=False, confidence=0.75,
        ))

    # If a database feature is present but no DB was named, infer SQLite
    if "database" in feature_names and not any(
        k in keyword_canonicals for k in ("sqlite", "postgres", "mysql", "mongodb", "redis")
    ):
        inferred.append(Technology(
            category="database", name="SQLite", role="data_storage",
            explicit=False, confidence=0.7,
        ))

    # Downloader bot → yt-dlp
    if bot_type == "downloader" and "yt-dlp" not in keyword_canonicals:
        inferred.append(Technology(
            category="library", name="yt-dlp", role="media_downloader",
            explicit=False, confidence=0.7,
        ))

    # AI assistant → OpenAI
    if bot_type == "ai_assistant" and "openai" not in keyword_canonicals:
        inferred.append(Technology(
            category="external_api", name="OpenAI API", role="ai_provider",
            explicit=False, confidence=0.65,
        ))

    # Store bot → payments may need a payment gateway
    if bot_type == "store" and "payments" in feature_names:
        if not any(k in keyword_canonicals for k in ("stripe", "paypal")):
            inferred.append(Technology(
                category="external_api", name="Payment Gateway",
                role="payment_processor", explicit=False, confidence=0.5,
            ))

    # Media download → ffmpeg for media processing
    if "media_download" in feature_names and "ffmpeg" not in keyword_canonicals:
        inferred.append(Technology(
            category="library", name="FFmpeg", role="media_processing",
            explicit=False, confidence=0.6,
        ))

    # File upload → requests/httpx for HTTP handling
    if "file_upload" in feature_names and "requests" not in keyword_canonicals:
        inferred.append(Technology(
            category="library", name="requests/httpx", role="http_client",
            explicit=False, confidence=0.5,
        ))

    return inferred


# ---------------------------------------------------------------------------#
# Main entry
# ---------------------------------------------------------------------------#

def run(state: Dict, report: AnalysisReport) -> List[str]:
    """Extract technologies from the keyword matches and infer others.

    Writes:
        report.technologies ← list of Technology objects.
        state["explicit_technologies"] ← set of explicit tech names.
        state["inferred_technologies"] ← set of inferred tech names.
    """
    warnings: List[str] = []

    keyword_canonicals: set = state.get("keyword_canonicals", set())
    bot_type: str = state.get("primary_bot_type", "general")
    feature_names: set = state.get("feature_names", set())

    # Explicit technologies
    explicit_techs: List[Technology] = []
    for canonical in keyword_canonicals:
        if canonical in _TECH_KEYWORD_MAP:
            explicit_techs.append(_TECH_KEYWORD_MAP[canonical])

    # Inferred technologies
    inferred_techs = _infer_technologies(
        bot_type, feature_names, keyword_canonicals,
    )

    # Merge, removing duplicates (explicit takes precedence)
    all_techs: List[Technology] = list(explicit_techs)
    explicit_names = {t.name for t in explicit_techs}
    for tech in inferred_techs:
        if tech.name not in explicit_names:
            all_techs.append(tech)

    report.technologies = all_techs
    state["explicit_technologies"] = explicit_names
    state["inferred_technologies"] = {
        t.name for t in inferred_techs if t.name not in explicit_names
    }

    if not all_techs:
        warnings.append("No technologies were extracted from the request.")

    return warnings


__all__ = ["run"]
