"""
Intelligence Graph Engine package (Specification 011).

This package contains the intelligence graph engine — the engine that
builds the complete, authoritative, intelligent graph of the entire
project by converting the seven upstream artefacts into a single
:class:`ProjectIntelligenceGraph`.  The engine does **not** write
code, create files, or make build decisions.  Its sole function is to
produce the single authoritative graph that every downstream engine
can query for any piece of project information and reach any element
in very few steps.

Public surface
--------------
* :class:`IntelligenceGraphEngine` — the engine itself.
* :class:`ProjectIntelligenceGraph` and all of its sub-dataclasses
  (:class:`GraphNode`, :class:`GraphEdge`, :class:`GraphFinding`,
  :class:`GraphIndices`, :class:`GraphProvenance`).
* :class:`GraphBuilder` — the node/edge builder.
* :class:`GraphNavigator` — the O(1) index builder.
* :class:`CircularDetector` — the structural-problem detector.
* :class:`GraphValidator` — the internal-consistency validator.
* Node-type, edge-kind, category, source-artefact, and severity
  constants.
"""

from __future__ import annotations

from .intelligence_graph_engine import IntelligenceGraphEngine
from .graph_data import (
    ProjectIntelligenceGraph,
    GraphNode,
    GraphEdge,
    GraphFinding,
    GraphIndices,
    GraphProvenance,
    # Source-artefact constants
    SOURCE_BLUEPRINT,
    SOURCE_VALIDATION,
    SOURCE_STRUCTURE,
    SOURCE_COMPONENT_REGISTRY,
    SOURCE_FILE_PLAN,
    SOURCE_DEPENDENCY_REPORT,
    SOURCE_PROJECT_CONTEXT,
    ALL_SOURCES,
    # Severity constants
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SEVERITY_INFO,
    ALL_SEVERITIES,
    # Node-type constants
    NODE_TYPE_PROJECT,
    NODE_TYPE_FOLDER,
    NODE_TYPE_FILE,
    NODE_TYPE_CLASS,
    NODE_TYPE_FUNCTION,
    NODE_TYPE_INTERFACE,
    NODE_TYPE_COMPONENT,
    NODE_TYPE_FEATURE,
    NODE_TYPE_DEPENDENCY,
    NODE_TYPE_LIBRARY,
    NODE_TYPE_DATABASE_TABLE,
    NODE_TYPE_ROUTE,
    NODE_TYPE_COMMAND,
    NODE_TYPE_CONFIGURATION,
    NODE_TYPE_ENVIRONMENT_VARIABLE,
    NODE_TYPE_SERVICE,
    NODE_TYPE_MIDDLEWARE,
    NODE_TYPE_REPOSITORY,
    NODE_TYPE_STAGE,
    ALL_NODE_TYPES,
    # Edge-kind constants
    EDGE_USES,
    EDGE_IMPORTS,
    EDGE_DEPENDS_ON,
    EDGE_CALLS,
    EDGE_CREATES,
    EDGE_READS,
    EDGE_WRITES,
    EDGE_EXTENDS,
    EDGE_IMPLEMENTS,
    EDGE_CONTAINS,
    EDGE_REFERENCES,
    EDGE_REQUIRED_BY,
    ALL_EDGE_KINDS,
    # Category constants
    CATEGORY_CIRCULAR_DEPENDENCY,
    CATEGORY_BROKEN_REFERENCE,
    CATEGORY_UNUSED_COMPONENT,
    CATEGORY_ORPHAN_FILE,
    CATEGORY_DEAD_COMPONENT,
    CATEGORY_CONSISTENCY,
    CATEGORY_STRUCTURE,
    ALL_CATEGORIES,
)
from .graph_builder import GraphBuilder
from .graph_navigator import GraphNavigator
from .circular_detector import CircularDetector
from .graph_validator import GraphValidator

__all__ = [
    # Engine
    "IntelligenceGraphEngine",
    # Data model
    "ProjectIntelligenceGraph",
    "GraphNode",
    "GraphEdge",
    "GraphFinding",
    "GraphIndices",
    "GraphProvenance",
    # Source-artefact constants
    "SOURCE_BLUEPRINT",
    "SOURCE_VALIDATION",
    "SOURCE_STRUCTURE",
    "SOURCE_COMPONENT_REGISTRY",
    "SOURCE_FILE_PLAN",
    "SOURCE_DEPENDENCY_REPORT",
    "SOURCE_PROJECT_CONTEXT",
    "ALL_SOURCES",
    # Severity constants
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "SEVERITY_INFO",
    "ALL_SEVERITIES",
    # Node-type constants
    "NODE_TYPE_PROJECT",
    "NODE_TYPE_FOLDER",
    "NODE_TYPE_FILE",
    "NODE_TYPE_CLASS",
    "NODE_TYPE_FUNCTION",
    "NODE_TYPE_INTERFACE",
    "NODE_TYPE_COMPONENT",
    "NODE_TYPE_FEATURE",
    "NODE_TYPE_DEPENDENCY",
    "NODE_TYPE_LIBRARY",
    "NODE_TYPE_DATABASE_TABLE",
    "NODE_TYPE_ROUTE",
    "NODE_TYPE_COMMAND",
    "NODE_TYPE_CONFIGURATION",
    "NODE_TYPE_ENVIRONMENT_VARIABLE",
    "NODE_TYPE_SERVICE",
    "NODE_TYPE_MIDDLEWARE",
    "NODE_TYPE_REPOSITORY",
    "NODE_TYPE_STAGE",
    "ALL_NODE_TYPES",
    # Edge-kind constants
    "EDGE_USES",
    "EDGE_IMPORTS",
    "EDGE_DEPENDS_ON",
    "EDGE_CALLS",
    "EDGE_CREATES",
    "EDGE_READS",
    "EDGE_WRITES",
    "EDGE_EXTENDS",
    "EDGE_IMPLEMENTS",
    "EDGE_CONTAINS",
    "EDGE_REFERENCES",
    "EDGE_REQUIRED_BY",
    "ALL_EDGE_KINDS",
    # Category constants
    "CATEGORY_CIRCULAR_DEPENDENCY",
    "CATEGORY_BROKEN_REFERENCE",
    "CATEGORY_UNUSED_COMPONENT",
    "CATEGORY_ORPHAN_FILE",
    "CATEGORY_DEAD_COMPONENT",
    "CATEGORY_CONSISTENCY",
    "CATEGORY_STRUCTURE",
    "ALL_CATEGORIES",
    # Helpers
    "GraphBuilder",
    "GraphNavigator",
    "CircularDetector",
    "GraphValidator",
]
