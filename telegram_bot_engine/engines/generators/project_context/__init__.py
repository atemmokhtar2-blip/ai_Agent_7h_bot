"""
Project Context Engine package (Specification 010).

This package contains the project context engine — the engine that
builds the complete, authoritative, unified understanding of the
entire project by merging the six upstream artefacts into a single
:class:`ProjectContext`.  The engine does **not** write code, create
files, or make build decisions.  Its sole function is to produce the
single authoritative context that every downstream engine can query
for any piece of project information.

Public surface
--------------
* :class:`ProjectContextEngine` — the engine itself.
* :class:`ProjectContext` and all of its sub-dataclasses
  (:class:`ProjectGoal`, :class:`FeatureSummary`,
  :class:`ComponentSummary`, :class:`FileSummary`,
  :class:`DependencySummary`, :class:`RelationshipSummary`,
  :class:`ExecutionStage`, :class:`ContextLink`,
  :class:`ExpansionPoint`, :class:`ContextFinding`,
  :class:`LinkIndices`, :class:`SourceProvenance`).
* :class:`ContextAssembler` — the merge helper.
* :class:`ContextLinker` — the link index builder.
* :class:`ContextValidator` — the context validator.
* :class:`BlueprintReader` — the blueprint reader.
* :class:`ValidationReader` — the validation reader.
* :class:`StructureReader` — the structure reader.
* :class:`RegistryReader` — the registry reader.
* :class:`FilePlanReader` — the file plan reader.
* :class:`DependencyReader` — the dependency reader.
* Source-artefact, severity, and link-kind constants.
"""

from __future__ import annotations

from .project_context_engine import ProjectContextEngine
from .context_data import (
    ProjectContext,
    ProjectGoal,
    FeatureSummary,
    ComponentSummary,
    FileSummary,
    DependencySummary,
    RelationshipSummary,
    ExecutionStage,
    ContextLink,
    ExpansionPoint,
    ContextFinding,
    LinkIndices,
    SourceProvenance,
    # Source-artefact constants
    SOURCE_BLUEPRINT,
    SOURCE_VALIDATION,
    SOURCE_STRUCTURE,
    SOURCE_COMPONENT_REGISTRY,
    SOURCE_FILE_PLAN,
    SOURCE_DEPENDENCY_REPORT,
    ALL_SOURCES,
    # Severity constants
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SEVERITY_INFO,
    ALL_SEVERITIES,
    # Link-kind constants
    LINK_FEATURE_TO_COMPONENT,
    LINK_COMPONENT_TO_FILE,
    LINK_FILE_TO_DEPENDENCY,
    LINK_DEPENDENCY_TO_STAGE,
    LINK_COMPONENT_TO_STAGE,
    LINK_FEATURE_TO_STAGE,
    ALL_LINK_KINDS,
)
from .context_assembler import ContextAssembler
from .context_linker import ContextLinker
from .context_validator import ContextValidator
from .blueprint_reader import BlueprintReader
from .validation_reader import ValidationReader
from .structure_reader import StructureReader
from .registry_reader import RegistryReader
from .file_plan_reader import FilePlanReader
from .dependency_reader import DependencyReader

__all__ = [
    # Engine
    "ProjectContextEngine",
    # Data model
    "ProjectContext",
    "ProjectGoal",
    "FeatureSummary",
    "ComponentSummary",
    "FileSummary",
    "DependencySummary",
    "RelationshipSummary",
    "ExecutionStage",
    "ContextLink",
    "ExpansionPoint",
    "ContextFinding",
    "LinkIndices",
    "SourceProvenance",
    # Source-artefact constants
    "SOURCE_BLUEPRINT",
    "SOURCE_VALIDATION",
    "SOURCE_STRUCTURE",
    "SOURCE_COMPONENT_REGISTRY",
    "SOURCE_FILE_PLAN",
    "SOURCE_DEPENDENCY_REPORT",
    "ALL_SOURCES",
    # Severity constants
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "SEVERITY_INFO",
    "ALL_SEVERITIES",
    # Link-kind constants
    "LINK_FEATURE_TO_COMPONENT",
    "LINK_COMPONENT_TO_FILE",
    "LINK_FILE_TO_DEPENDENCY",
    "LINK_DEPENDENCY_TO_STAGE",
    "LINK_COMPONENT_TO_STAGE",
    "LINK_FEATURE_TO_STAGE",
    "ALL_LINK_KINDS",
    # Helpers
    "ContextAssembler",
    "ContextLinker",
    "ContextValidator",
    "BlueprintReader",
    "ValidationReader",
    "StructureReader",
    "RegistryReader",
    "FilePlanReader",
    "DependencyReader",
]
