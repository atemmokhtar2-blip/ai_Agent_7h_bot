"""
Analysis stages package — the 10 stages of the Core Request Analyzer.

Each module in this package implements a single, independent analysis
stage.  The stages are pure functions that receive a mutable *state*
dictionary and an :class:`AnalysisReport`, mutate both as needed, and
return a list of warnings (possibly empty).

The stages are designed to be run sequentially by the
:class:`~telegram_bot_engine.engines.generators.analyzer.analyzer_engine.AnalyzerEngine`.
"""

from .stage1_cleaner import run as stage1_clean
from .stage2_segmenter import run as stage2_segment
from .stage3_keyword_extractor import run as stage3_keywords
from .stage4_classifier import run as stage4_classify
from .stage5_feature_extractor import run as stage5_features
from .stage6_technology_extractor import run as stage6_technologies
from .stage7_relationship_analyzer import run as stage7_relationships
from .stage8_conflict_detector import run as stage8_conflicts
from .stage9_missing_info_detector import run as stage9_missing_info
from .stage10_report_builder import run as stage10_report

__all__ = [
    "stage1_clean",
    "stage2_segment",
    "stage3_keywords",
    "stage4_classify",
    "stage5_features",
    "stage6_technologies",
    "stage7_relationships",
    "stage8_conflicts",
    "stage9_missing_info",
    "stage10_report",
]
