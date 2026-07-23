"""
Stage 8 — Conflict detection.

Responsibilities:
    * Detect conflicting or ambiguous choices in the request.
    * Produce a list of :class:`Conflict` objects with kind, description,
      items, severity, and resolution hint.
    * Severity is ``"error"`` for blocking conflicts and ``"warning"``
      for ambiguous or non-blocking issues.

Detected conflict types:
    * ``conflicting_database`` — multiple databases mentioned (SQLite +
      PostgreSQL).
    * ``conflicting_update_mode`` — both polling and webhook mentioned.
    * ``conflicting_framework`` — multiple Telegram frameworks mentioned.
    * ``conflicting_language`` — both Python and Node.js mentioned.
    * ``ambiguous_bot_type`` — multiple bot types with similar priority.
"""

from __future__ import annotations

from typing import Dict, List

from ..analysis_report import AnalysisReport, Conflict


# ---------------------------------------------------------------------------#
# Conflict definitions
# ---------------------------------------------------------------------------#

_DATABASE_NAMES = {"sqlite", "postgres", "mysql", "mongodb", "redis"}
_DATABASE_DISPLAY = {
    "sqlite": "SQLite",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
}

_FRAMEWORK_NAMES = {
    "python_telegram_bot": "python-telegram-bot",
    "aiogram": "aiogram",
    "pyrogram": "pyrogram",
    "telethon": "telethon",
}

_LANGUAGE_NAMES = {"python", "nodejs"}


def run(state: Dict, report: AnalysisReport) -> List[str]:
    """Detect conflicts in the analysis so far.

    Writes:
        report.conflicts ← list of Conflict objects.
    """
    warnings: List[str] = []

    conflicts: List[Conflict] = []
    keyword_canonicals: set = state.get("keyword_canonicals", set())

    # 1. Conflicting databases
    db_found = _DATABASE_NAMES & keyword_canonicals
    if len(db_found) > 1:
        db_display = [_DATABASE_DISPLAY[d] for d in db_found]
        conflicts.append(Conflict(
            kind="conflicting_database",
            description=(
                f"Multiple databases mentioned: {', '.join(db_display)}. "
                f"Only one primary database should be used."
            ),
            items=list(db_display),
            severity="error",
            resolution_hint=(
                "Choose a single database. For small bots use SQLite; "
                "for production use PostgreSQL or MySQL."
            ),
        ))

    # 2. Conflicting update mode (polling vs webhook)
    has_polling = "polling" in keyword_canonicals
    has_webhook = "webhook" in keyword_canonicals
    if has_polling and has_webhook:
        conflicts.append(Conflict(
            kind="conflicting_update_mode",
            description=(
                "Both polling and webhook update modes were mentioned. "
                "A bot should use only one update mode."
            ),
            items=["polling", "webhook"],
            severity="error",
            resolution_hint=(
                "Choose either polling (simpler, good for development) "
                "or webhook (better for production)."
            ),
        ))

    # 3. Conflicting frameworks
    fw_found = set(_FRAMEWORK_NAMES.keys()) & keyword_canonicals
    if len(fw_found) > 1:
        fw_display = [_FRAMEWORK_NAMES[f] for f in fw_found]
        conflicts.append(Conflict(
            kind="conflicting_framework",
            description=(
                f"Multiple Telegram bot frameworks mentioned: "
                f"{', '.join(fw_display)}. Only one framework should be used."
            ),
            items=list(fw_display),
            severity="error",
            resolution_hint="Choose a single Telegram bot framework.",
        ))

    # 4. Conflicting languages
    lang_found = _LANGUAGE_NAMES & keyword_canonicals
    if len(lang_found) > 1:
        conflicts.append(Conflict(
            kind="conflicting_language",
            description=(
                "Multiple programming languages mentioned (Python and "
                "Node.js). The engine generates Python code only."
            ),
            items=["Python", "Node.js"],
            severity="error",
            resolution_hint="Use Python as the implementation language.",
        ))

    # 5. Ambiguous bot type — multiple types with similar confidence
    if len(report.bot_types) > 1:
        top = report.bot_types[0]
        second = report.bot_types[1]
        if top.confidence > 0 and second.confidence > 0:
            ratio = second.confidence / top.confidence
            if ratio > 0.8:
                conflicts.append(Conflict(
                    kind="ambiguous_bot_type",
                    description=(
                        f"Two bot types have similar confidence: "
                        f"'{top.type}' (conf={top.confidence:.2f}) and "
                        f"'{second.type}' (conf={second.confidence:.2f}). "
                        f"The primary type may not be correct."
                    ),
                    items=[top.type, second.type],
                    severity="warning",
                    resolution_hint=(
                        f"Clarify whether the bot is primarily a '{top.type}' "
                        f"or '{second.type}' bot."
                    ),
                ))

    report.conflicts = conflicts

    # Warnings list is separate from Conflict objects
    if conflicts:
        error_count = sum(1 for c in conflicts if c.severity == "error")
        warning_count = sum(1 for c in conflicts if c.severity == "warning")
        if error_count:
            warnings.append(
                f"{error_count} error-level conflict(s) detected."
            )
        if warning_count:
            warnings.append(
                f"{warning_count} warning-level conflict(s) detected."
            )

    return warnings


__all__ = ["run"]
