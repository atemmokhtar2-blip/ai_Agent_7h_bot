"""
Requirement Intelligence Engine package (Specification 012).

This package contains the requirement intelligence engine — the engine
that understands the user's request with the highest possible
precision and converts it into a precise set of engineering
requirements.  The engine does **not** write code, create files,
choose libraries, or make build decisions.  Its sole function is to
produce the *Requirement Intelligence Report* — a structured,
validated, dependency-aware catalogue of every requirement the
project must satisfy.

Public surface
--------------
* :class:`RequirementIntelligenceEngine` — the engine itself.
* :class:`RequirementIntelligenceReport` and all of its sub-dataclasses
  (:class:`IntentDimension`, :class:`IntentAnalysis`,
  :class:`Requirement`, :class:`RequiredQuestion`,
  :class:`AmbiguityPoint`, :class:`RequirementConflict`,
  :class:`QualityViolation`, :class:`ReportFinding`,
  :class:`ReportProvenance`).
* :class:`RequestReader`, :class:`ContextReader`, :class:`GraphReader`,
  :class:`KnowledgeReader` — the four data-source readers.
* :class:`IntentAnalyzer` — the intent-analysis helper.
* :class:`RequirementClassifier` — the requirement classifier.
* :class:`MissingDetector` — the missing-information / ambiguity
  detector.
* :class:`ConflictDetector` — the requirement-conflict detector.
* :class:`PriorityAssigner` — the priority-assignment helper.
* :class:`QualityValidator` — the report quality validator.
* :class:`ReportAssembler` — the final-report assembler.
* :class:`RequestData`, :class:`ContextData`, :class:`GraphData`,
  :class:`KnowledgeData` — the intermediate data containers produced by
  the readers.
* Source-artefact, severity, category, priority, intent-dimension,
  quality-level, conflict-kind, and ambiguity-kind constants.
"""

from __future__ import annotations

from .requirement_intelligence_engine import RequirementIntelligenceEngine
from .report_data import (
    # Data model
    IntentDimension,
    IntentAnalysis,
    Requirement,
    RequiredQuestion,
    AmbiguityPoint,
    RequirementConflict,
    QualityViolation,
    ReportFinding,
    ReportProvenance,
    RequirementIntelligenceReport,
    # Source-artefact constants
    SOURCE_USER_REQUEST,
    SOURCE_PROJECT_CONTEXT,
    SOURCE_INTELLIGENCE_GRAPH,
    SOURCE_KNOWLEDGE_BASE,
    ALL_SOURCES,
    # Severity constants
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SEVERITY_INFO,
    ALL_SEVERITIES,
    # Category constants
    CATEGORY_FUNCTIONAL,
    CATEGORY_NON_FUNCTIONAL,
    CATEGORY_PERFORMANCE,
    CATEGORY_SECURITY,
    CATEGORY_ARCHITECTURE,
    CATEGORY_TESTING,
    CATEGORY_DEPLOYMENT,
    CATEGORY_FUTURE_EXPANSION,
    CATEGORY_IMPLICIT,
    ALL_CATEGORIES,
    CATEGORY_DISPLAY_NAMES,
    # Priority constants
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_NORMAL,
    PRIORITY_LOW,
    ALL_PRIORITIES,
    PRIORITY_RANKS,
    # Intent-dimension constants
    INTENT_DIMENSION_WANTS,
    INTENT_DIMENSION_DOES_NOT_WANT,
    INTENT_DIMENSION_FINAL_GOAL,
    INTENT_DIMENSION_CONSTRAINTS,
    INTENT_DIMENSION_QUALITY_LEVEL,
    ALL_INTENT_DIMENSIONS,
    # Quality-level constants
    QUALITY_LEVEL_MINIMAL,
    QUALITY_LEVEL_STANDARD,
    QUALITY_LEVEL_HIGH,
    QUALITY_LEVEL_PRODUCTION,
    ALL_QUALITY_LEVELS,
    # Conflict-kind constants
    CONFLICT_CONTRADICTORY,
    CONFLICT_ILLOGICAL,
    CONFLICT_IMPOSSIBLE,
    CONFLICT_DUPLICATE,
    ALL_CONFLICT_KINDS,
    # Ambiguity-kind constants
    AMBIGUITY_VAGUE,
    AMBIGUITY_UNDER_SPECIFIED,
    AMBIGUITY_MULTIPLE_INTERPRETATIONS,
    AMBIGUITY_MISSING_CONTEXT,
    ALL_AMBIGUITY_KINDS,
)
from .request_reader import RequestReader, RequestData
from .context_reader import ContextReader, ContextData
from .graph_reader import GraphReader, GraphData
from .knowledge_reader import KnowledgeReader, KnowledgeData
from .intent_analyzer import IntentAnalyzer
from .requirement_classifier import RequirementClassifier
from .missing_detector import MissingDetector
from .conflict_detector import ConflictDetector
from .priority_assigner import PriorityAssigner
from .quality_validator import QualityValidator
from .report_assembler import ReportAssembler

__all__ = [
    # Engine
    "RequirementIntelligenceEngine",
    # Data model
    "IntentDimension",
    "IntentAnalysis",
    "Requirement",
    "RequiredQuestion",
    "AmbiguityPoint",
    "RequirementConflict",
    "QualityViolation",
    "ReportFinding",
    "ReportProvenance",
    "RequirementIntelligenceReport",
    # Source-artefact constants
    "SOURCE_USER_REQUEST",
    "SOURCE_PROJECT_CONTEXT",
    "SOURCE_INTELLIGENCE_GRAPH",
    "SOURCE_KNOWLEDGE_BASE",
    "ALL_SOURCES",
    # Severity constants
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "SEVERITY_INFO",
    "ALL_SEVERITIES",
    # Category constants
    "CATEGORY_FUNCTIONAL",
    "CATEGORY_NON_FUNCTIONAL",
    "CATEGORY_PERFORMANCE",
    "CATEGORY_SECURITY",
    "CATEGORY_ARCHITECTURE",
    "CATEGORY_TESTING",
    "CATEGORY_DEPLOYMENT",
    "CATEGORY_FUTURE_EXPANSION",
    "CATEGORY_IMPLICIT",
    "ALL_CATEGORIES",
    "CATEGORY_DISPLAY_NAMES",
    # Priority constants
    "PRIORITY_CRITICAL",
    "PRIORITY_HIGH",
    "PRIORITY_NORMAL",
    "PRIORITY_LOW",
    "ALL_PRIORITIES",
    "PRIORITY_RANKS",
    # Intent-dimension constants
    "INTENT_DIMENSION_WANTS",
    "INTENT_DIMENSION_DOES_NOT_WANT",
    "INTENT_DIMENSION_FINAL_GOAL",
    "INTENT_DIMENSION_CONSTRAINTS",
    "INTENT_DIMENSION_QUALITY_LEVEL",
    "ALL_INTENT_DIMENSIONS",
    # Quality-level constants
    "QUALITY_LEVEL_MINIMAL",
    "QUALITY_LEVEL_STANDARD",
    "QUALITY_LEVEL_HIGH",
    "QUALITY_LEVEL_PRODUCTION",
    "ALL_QUALITY_LEVELS",
    # Conflict-kind constants
    "CONFLICT_CONTRADICTORY",
    "CONFLICT_ILLOGICAL",
    "CONFLICT_IMPOSSIBLE",
    "CONFLICT_DUPLICATE",
    "ALL_CONFLICT_KINDS",
    # Ambiguity-kind constants
    "AMBIGUITY_VAGUE",
    "AMBIGUITY_UNDER_SPECIFIED",
    "AMBIGUITY_MULTIPLE_INTERPRETATIONS",
    "AMBIGUITY_MISSING_CONTEXT",
    "ALL_AMBIGUITY_KINDS",
    # Readers + intermediate data
    "RequestReader",
    "RequestData",
    "ContextReader",
    "ContextData",
    "GraphReader",
    "GraphData",
    "KnowledgeReader",
    "KnowledgeData",
    # Helpers
    "IntentAnalyzer",
    "RequirementClassifier",
    "MissingDetector",
    "ConflictDetector",
    "PriorityAssigner",
    "QualityValidator",
    "ReportAssembler",
]
