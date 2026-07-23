"""
Core Request Analyzer package.

This package implements the Core Request Analyzer Engine — a 10-stage
analysis pipeline that produces an :class:`AnalysisReport` as the
authoritative description of the user's request.

The analyzer engine is the first engine in the generation pipeline.  It
performs pure analysis (no code generation) and produces a structured
report that all downstream engines read instead of the raw user message.

Modules:
    * ``analysis_report`` — the data model (AnalysisReport and sub-types).
    * ``analyzer_engine`` — the main engine class that orchestrates stages.
    * ``stages`` — the 10 individual analysis stage modules.
"""

from .analysis_report import (
    AnalysisReport,
    Token,
    KeywordMatch,
    BotTypeEntry,
    Feature,
    Technology,
    Relationship,
    Conflict,
    MissingInfo,
    ConfidenceScore,
)
from .analyzer_engine import AnalyzerEngine

__all__ = [
    "AnalyzerEngine",
    "AnalysisReport",
    "Token",
    "KeywordMatch",
    "BotTypeEntry",
    "Feature",
    "Technology",
    "Relationship",
    "Conflict",
    "MissingInfo",
    "ConfidenceScore",
]
