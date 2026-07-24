"""
Project Context data model (Specification 010).

This module defines the :class:`ProjectContext` — the complete,
authoritative, unified understanding of the entire project.  It is the
**single** artefact produced by the
:class:`~telegram_bot_engine.engines.generators.project_context.ProjectContextEngine`.

The Project Context is built by merging **six** read-only artefacts:

1. the ``project_blueprint`` (produced by the Project Planning Engine),
2. the ``blueprint_validation_report`` (produced by the Blueprint
   Validator Engine),
3. the ``project_structure_map`` (produced by the Structure Generation
   Engine),
4. the ``component_registry`` (produced by the Component Detection
   Engine),
5. the ``file_generation_plan`` (produced by the File Generation
   Planning Engine),
6. the ``dependency_resolution_report`` (produced by the Dependency
   Resolution Engine).

The engine is **forbidden** from reading the user's request.

Design principles
-----------------
* **One unified model.**  Every downstream engine reads the
  :class:`ProjectContext` instead of re-reading the individual upstream
  artefacts.  This eliminates redundant parsing and keeps the
  understanding of the project in a single place.
* **Traceability.**  Every piece of information inside the Project
  Context records the artefact it came from (``source_artefact``).
  Any decision taken by a downstream engine can trace its data back
  to the original source.
* **Context linking.**  Features are linked to the components that
  implement them, components are linked to the files that contain them,
  files are linked to the dependencies they require, and everything is
  linked to the execution stage it belongs to.  A downstream engine can
  start from any point (a feature, a component, a file, a dependency)
  and reach any other point in O(1) time using the link indices.
* **No build decisions.**  The Project Context provides **information**,
  not decisions.  It does not decide which file to generate first, which
  library to install first, or how to structure the code.  It only
  provides the data so that decision-making engines can act.
* **Validation.**  The context is validated for internal consistency:
  no conflicting data, no unknown elements, no features without
  components, no components without files, no files without
  responsibility.
* **Performance.**  The context is built once and queried many times.
  Look-up indices (by name, by type, by source) are precomputed so that
  downstream engines can access any information in constant time
  without re-analysing the project.
* **Scalability.**  The context is a plain data container that grows
  linearly with the number of features, components, files, and
  dependencies.  No O(n²) operations are performed during
  construction or querying.  The context works equally well for small,
  medium, and very large projects.

The context is a plain data container — no logic lives here.  The
context engine and its helpers populate it; downstream consumers (the
code generators, the manager, tests) read it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------#
# Source-artefact constants
# ---------------------------------------------------------------------------#
#
# Every sub-model inside the Project Context records the artefact it was
# derived from.  These constants are the stable identifiers for the six
# upstream artefacts.

SOURCE_BLUEPRINT = "blueprint"
SOURCE_VALIDATION = "validation"
SOURCE_STRUCTURE = "structure"
SOURCE_COMPONENT_REGISTRY = "component_registry"
SOURCE_FILE_PLAN = "file_plan"
SOURCE_DEPENDENCY_REPORT = "dependency_report"

ALL_SOURCES = (
    SOURCE_BLUEPRINT,
    SOURCE_VALIDATION,
    SOURCE_STRUCTURE,
    SOURCE_COMPONENT_REGISTRY,
    SOURCE_FILE_PLAN,
    SOURCE_DEPENDENCY_REPORT,
)


# ---------------------------------------------------------------------------#
# Severity constants
# ---------------------------------------------------------------------------#

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

ALL_SEVERITIES = (SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO)


# ---------------------------------------------------------------------------#
# Context-link kind constants
# ---------------------------------------------------------------------------#
#
# The link kinds describe the type of relationship between two linked
# elements in the context graph.  These are used by the ContextLinker
# to build the link indices.

LINK_FEATURE_TO_COMPONENT = "feature_to_component"
LINK_COMPONENT_TO_FILE = "component_to_file"
LINK_FILE_TO_DEPENDENCY = "file_to_dependency"
LINK_DEPENDENCY_TO_STAGE = "dependency_to_stage"
LINK_COMPONENT_TO_STAGE = "component_to_stage"
LINK_FEATURE_TO_STAGE = "feature_to_stage"

ALL_LINK_KINDS = (
    LINK_FEATURE_TO_COMPONENT,
    LINK_COMPONENT_TO_FILE,
    LINK_FILE_TO_DEPENDENCY,
    LINK_DEPENDENCY_TO_STAGE,
    LINK_COMPONENT_TO_STAGE,
    LINK_FEATURE_TO_STAGE,
)


# ---------------------------------------------------------------------------#
# Project goal
# ---------------------------------------------------------------------------#

@dataclass
class ProjectGoal:
    """The high-level goal and identity of the project.

    This is the top-level summary that every downstream engine should
    understand before making any decision.  It is derived from the
    :class:`ProjectBlueprint`'s identity section.

    Attributes:
        name: The machine-friendly project name (slug).
        display_name: The human-readable project name.
        bot_type: The detected bot type (e.g. ``"store"``,
            ``"group_admin"``, ``"ai_assistant"``).
        primary_goal: A one-sentence description of what the project
            does.
        language: The programming language (e.g. ``"python"``).
        language_version: The language version (e.g. ``"3.11"``).
        framework: The Telegram bot framework (e.g.
            ``"python-telegram-bot"``).
        database: The chosen database backend (or empty string when
            no database is needed).
        source_artefact: The artefact this goal was derived from
            (always ``"blueprint"``).
    """

    name: str = ""
    display_name: str = ""
    bot_type: str = "general"
    primary_goal: str = ""
    language: str = "python"
    language_version: str = "3.11"
    framework: str = "python-telegram-bot"
    database: str = ""
    source_artefact: str = SOURCE_BLUEPRINT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "bot_type": self.bot_type,
            "primary_goal": self.primary_goal,
            "language": self.language,
            "language_version": self.language_version,
            "framework": self.framework,
            "database": self.database,
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Feature summary
# ---------------------------------------------------------------------------#

@dataclass
class FeatureSummary:
    """A single feature in the project context.

    This is a lightweight summary of a :class:`FeatureUnit` from the
    blueprint.  It records the feature's identity and the components
    that implement it.

    Attributes:
        name: The feature name (machine-friendly).
        display_name: The human-readable feature name.
        description: What the feature does.
        priority: The feature priority (lower values are built
            first).
        source_feature: The source feature unit name in the
            blueprint (same as ``name`` for most features).
        components: The names of the detected components that
            implement this feature.
        source_artefact: The artefact this summary was derived
            from (always ``"blueprint"`` for the identity fields;
            ``"component_registry"`` for the component links).
    """

    name: str
    display_name: str = ""
    description: str = ""
    priority: int = 100
    source_feature: str = ""
    components: List[str] = field(default_factory=list)
    source_artefact: str = SOURCE_BLUEPRINT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "priority": self.priority,
            "source_feature": self.source_feature,
            "components": list(self.components),
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Component summary
# ---------------------------------------------------------------------------#

@dataclass
class ComponentSummary:
    """A single detected component in the project context.

    This is a lightweight summary of a :class:`DetectedComponent` from
    the component registry.  It records the component's identity, type,
    responsibility, location, and the files that implement it.

    Attributes:
        name: The component name (unique within the context).
        type: The component type (one of the ``COMPONENT_TYPE_*``
            constants from the registry).
        purpose: A short description of what the component is for.
        responsibility: The single, clear responsibility of the
            component.
        source_feature: The feature this component belongs to, if
            any.
        location: The relative path within the project where this
            component lives.
        build_order: The position in the build sequence (lower
            first).
        importance: The importance level (``"critical"``,
            ``"high"``, ``"normal"``, ``"low"``).
        files: The paths of the files that implement this
            component.
        dependencies: The names of the dependencies this component
            requires.
        depends_on: The names of other components this one depends
            on.
        depended_by: The names of components that depend on this
            one.
        source_artefact: The artefact this summary was derived
            from (always ``"component_registry"``).
    """

    name: str
    type: str = "utility"
    purpose: str = ""
    responsibility: str = ""
    source_feature: str = ""
    location: str = ""
    build_order: int = 100
    importance: str = "normal"
    files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    depended_by: List[str] = field(default_factory=list)
    source_artefact: str = SOURCE_COMPONENT_REGISTRY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "purpose": self.purpose,
            "responsibility": self.responsibility,
            "source_feature": self.source_feature,
            "location": self.location,
            "build_order": self.build_order,
            "importance": self.importance,
            "files": list(self.files),
            "dependencies": list(self.dependencies),
            "depends_on": list(self.depends_on),
            "depended_by": list(self.depended_by),
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# File summary
# ---------------------------------------------------------------------------#

@dataclass
class FileSummary:
    """A single planned file in the project context.

    This is a lightweight summary of a :class:`FilePlanEntry` from the
    file generation plan.  It records the file's identity, type,
    purpose, and the component it belongs to.

    Attributes:
        name: The file name (e.g. ``"main.py"``).
        path: The full relative path from the project root.
        file_type: The file type (one of the ``FILE_TYPE_*``
            constants from the file plan).
        purpose: What this file is for.
        folder: The folder path this file belongs to.
        responsible_engine: The engine that will build this file.
        generation_priority: The broad generation phase (lower
            values are generated first).
        build_order: The precise position in the generation
            sequence.
        source_component: The detected component this file
            belongs to.
        depends_on: The paths of other files this file depends
            on.
        depended_by: The paths of files that depend on this file.
        reason_for_existence: Why this file exists.
        contains_code: ``True`` when this file will contain
            executable code.
        source_artefact: The artefact this summary was derived
            from (always ``"file_plan"``).
    """

    name: str
    path: str
    file_type: str = "text"
    purpose: str = ""
    folder: str = ""
    responsible_engine: str = ""
    generation_priority: int = 20
    build_order: int = 0
    source_component: str = ""
    depends_on: List[str] = field(default_factory=list)
    depended_by: List[str] = field(default_factory=list)
    reason_for_existence: str = ""
    contains_code: bool = False
    source_artefact: str = SOURCE_FILE_PLAN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "file_type": self.file_type,
            "purpose": self.purpose,
            "folder": self.folder,
            "responsible_engine": self.responsible_engine,
            "generation_priority": self.generation_priority,
            "build_order": self.build_order,
            "source_component": self.source_component,
            "depends_on": list(self.depends_on),
            "depended_by": list(self.depended_by),
            "reason_for_existence": self.reason_for_existence,
            "contains_code": self.contains_code,
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Dependency summary
# ---------------------------------------------------------------------------#

@dataclass
class DependencySummary:
    """A single resolved dependency in the project context.

    This is a lightweight summary of a :class:`DependencyEntry` from
    the dependency resolution report.  It records the dependency's
    identity, type, version, and the components that require it.

    Attributes:
        name: The dependency name (e.g. ``"python-telegram-bot"``).
        type: The dependency type (``"library"``, ``"framework"``,
            ``"tool"``, etc.).
        suggested_version: The suggested version.
        version_constraint: The version constraint.
        reason: Why this dependency is needed.
        source_components: The detected component names that
            require this dependency.
        priority: The broad resolution phase (lower values are
            resolved first).
        load_order: The position in the load sequence.
        language: The programming language this dependency is for.
        framework: The framework this dependency belongs to.
        depends_on: The names of other dependencies this one
            depends on.
        depended_by: The names of dependencies that depend on
            this one.
        source_artefact: The artefact this summary was derived
            from (always ``"dependency_report"``).
    """

    name: str
    type: str = "library"
    suggested_version: str = "latest"
    version_constraint: str = ""
    reason: str = ""
    source_components: List[str] = field(default_factory=list)
    priority: int = 20
    load_order: int = 0
    language: str = ""
    framework: str = ""
    depends_on: List[str] = field(default_factory=list)
    depended_by: List[str] = field(default_factory=list)
    source_artefact: str = SOURCE_DEPENDENCY_REPORT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "suggested_version": self.suggested_version,
            "version_constraint": self.version_constraint,
            "reason": self.reason,
            "source_components": list(self.source_components),
            "priority": self.priority,
            "load_order": self.load_order,
            "language": self.language,
            "framework": self.framework,
            "depends_on": list(self.depends_on),
            "depended_by": list(self.depended_by),
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Relationship summary
# ---------------------------------------------------------------------------#

@dataclass
class RelationshipSummary:
    """A single relationship in the project context.

    Relationships are recorded from all upstream artefacts (blueprint
    component relationships, structure relationships, file
    relationships, dependency relationships, component-registry
    relationships).  Each relationship is normalised to a common format
    with a source, target, kind, and the artefact it came from.

    Attributes:
        source: The source element name (a feature, component,
            file, or dependency name).
        target: The target element name.
        kind: The relationship kind (``"depends_on"``,
            ``"uses"``, ``"calls"``, ``"managed_by"``,
            ``"stored_in"``, ``"contains"``, ``"imports"``,
            ``"configures"``, ``"documents"``, ``"tested_by"``,
            ``"requires"``, ``"extends"``, ``"conflicts_with"``,
            ``"replaces"``).
        description: A human-readable description.
        source_artefact: The artefact this relationship was
            derived from.
    """

    source: str
    target: str
    kind: str = "depends_on"
    description: str = ""
    source_artefact: str = SOURCE_BLUEPRINT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "description": self.description,
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Execution stage
# ---------------------------------------------------------------------------#

@dataclass
class ExecutionStage:
    """A single execution stage in the project context.

    This is derived from the blueprint's execution plan and the
    dependency resolution report's load order.  Each stage represents a
    phase in the build sequence and records the components, files, and
    dependencies that belong to it.

    Attributes:
        name: The stage name (e.g. ``"infrastructure"``,
            ``"core"``, ``"database"``, ``"features"``,
            ``"wiring"``, ``"entry"``, ``"docs"``, ``"tests"``).
        phase: The phase number (0-based).
        priority: The broad priority (lower values are built
            first).
        components: The names of the components in this stage.
        files: The paths of the files in this stage.
        dependencies: The names of the dependencies in this
            stage.
        source_artefact: The artefact this stage was derived
            from.
    """

    name: str
    phase: int = 0
    priority: int = 100
    components: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    source_artefact: str = SOURCE_BLUEPRINT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "phase": self.phase,
            "priority": self.priority,
            "components": list(self.components),
            "files": list(self.files),
            "dependencies": list(self.dependencies),
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Context link
# ---------------------------------------------------------------------------#

@dataclass
class ContextLink:
    """A single link in the context graph.

    Links connect elements across the different layers of the Project
    Context.  For example, a link of kind
    ``"feature_to_component"`` connects a feature to the component
    that implements it.  Links are precomputed by the
    :class:`ContextLinker` so that downstream engines can traverse the
    context graph in O(1) time.

    Attributes:
        source: The source element name.
        target: The target element name.
        kind: The link kind (one of the ``LINK_*`` constants).
        source_artefact: The artefact the link was derived from.
    """

    source: str
    target: str
    kind: str = LINK_FEATURE_TO_COMPONENT
    source_artefact: str = SOURCE_BLUEPRINT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Expansion point
# ---------------------------------------------------------------------------#

@dataclass
class ExpansionPoint:
    """A future expansion point in the project.

    This records areas where the project can be extended in the future
    without restructuring.  It is derived from the scalability flags on
    components, files, and dependencies, and from the blueprint's
    structure and features.

    Attributes:
        area: The area that can be expanded (e.g.
            ``"handlers"``, ``"commands"``, ``"services"``).
        description: A description of how the area can be
            expanded.
        source_artefact: The artefact this expansion point was
            derived from.
    """

    area: str
    description: str = ""
    source_artefact: str = SOURCE_BLUEPRINT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.area,
            "description": self.description,
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Context finding
# ---------------------------------------------------------------------------#

@dataclass
class ContextFinding:
    """A single finding produced during context building or validation.

    Attributes:
        severity: ``"error"``, ``"warning"``, or ``"info"``.
        code: A short, machine-readable code (e.g.
            ``"feature_without_components"``).
        message: A human-readable description.
        affected: The name of the affected element.
        resolution_hint: An optional suggestion on how to fix
            the issue.
        category: The finding category (``"linking"``,
            ``"validation"``, ``"consistency"``).
    """

    severity: str = SEVERITY_WARNING
    code: str = ""
    message: str = ""
    affected: str = ""
    resolution_hint: str = ""
    category: str = "validation"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "affected": self.affected,
            "resolution_hint": self.resolution_hint,
            "category": self.category,
        }


# ---------------------------------------------------------------------------#
# Link indices (precomputed for O(1) look-ups)
# ---------------------------------------------------------------------------#

@dataclass
class LinkIndices:
    """Precomputed look-up indices for the context graph.

    These indices are built by the :class:`ContextLinker` so that
    downstream engines can traverse the context in O(1) time without
    re-analysing the project.

    Attributes:
        feature_to_components: Feature name → list of component
            names.
        component_to_features: Component name → list of feature
            names.
        component_to_files: Component name → list of file paths.
        file_to_components: File path → list of component names.
        file_to_dependencies: File path → list of dependency
            names.
        dependency_to_files: Dependency name → list of file
            paths.
        dependency_to_components: Dependency name → list of
            component names.
        component_to_dependencies: Component name → list of
            dependency names.
        component_to_stage: Component name → stage name.
        feature_to_stage: Feature name → stage name.
        file_to_stage: File path → stage name.
        dependency_to_stage: Dependency name → stage name.
    """

    feature_to_components: Dict[str, List[str]] = field(default_factory=dict)
    component_to_features: Dict[str, List[str]] = field(default_factory=dict)
    component_to_files: Dict[str, List[str]] = field(default_factory=dict)
    file_to_components: Dict[str, List[str]] = field(default_factory=dict)
    file_to_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    dependency_to_files: Dict[str, List[str]] = field(default_factory=dict)
    dependency_to_components: Dict[str, List[str]] = field(default_factory=dict)
    component_to_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    component_to_stage: Dict[str, str] = field(default_factory=dict)
    feature_to_stage: Dict[str, str] = field(default_factory=dict)
    file_to_stage: Dict[str, str] = field(default_factory=dict)
    dependency_to_stage: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_to_components": {
                k: list(v) for k, v in self.feature_to_components.items()
            },
            "component_to_features": {
                k: list(v) for k, v in self.component_to_features.items()
            },
            "component_to_files": {
                k: list(v) for k, v in self.component_to_files.items()
            },
            "file_to_components": {
                k: list(v) for k, v in self.file_to_components.items()
            },
            "file_to_dependencies": {
                k: list(v) for k, v in self.file_to_dependencies.items()
            },
            "dependency_to_files": {
                k: list(v) for k, v in self.dependency_to_files.items()
            },
            "dependency_to_components": {
                k: list(v) for k, v in self.dependency_to_components.items()
            },
            "component_to_dependencies": {
                k: list(v) for k, v in self.component_to_dependencies.items()
            },
            "component_to_stage": dict(self.component_to_stage),
            "feature_to_stage": dict(self.feature_to_stage),
            "file_to_stage": dict(self.file_to_stage),
            "dependency_to_stage": dict(self.dependency_to_stage),
        }


# ---------------------------------------------------------------------------#
# Source provenance
# ---------------------------------------------------------------------------#

@dataclass
class SourceProvenance:
    """Records which upstream artefacts were used to build the context.

    This is the traceability record required by the specification: any
    decision taken by a downstream engine can trace its data back to
    the original source artefact.

    Attributes:
        blueprint_name: The name of the blueprint used.
        validation_status: The approval status of the blueprint.
        structure_map_name: The name of the structure map used.
        component_registry_name: The name of the component
            registry used.
        file_plan_name: The name of the file generation plan used.
        dependency_report_name: The name of the dependency
            resolution report used.
        all_sources_used: The list of all source artefact
            identifiers that contributed to the context.
    """

    blueprint_name: str = ""
    validation_status: str = ""
    structure_map_name: str = ""
    component_registry_name: str = ""
    file_plan_name: str = ""
    dependency_report_name: str = ""
    all_sources_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blueprint_name": self.blueprint_name,
            "validation_status": self.validation_status,
            "structure_map_name": self.structure_map_name,
            "component_registry_name": self.component_registry_name,
            "file_plan_name": self.file_plan_name,
            "dependency_report_name": self.dependency_report_name,
            "all_sources_used": list(self.all_sources_used),
        }


# ---------------------------------------------------------------------------#
# The full Project Context
# ---------------------------------------------------------------------------#

@dataclass
class ProjectContext:
    """The complete, authoritative, unified understanding of the project.

    This is the **only** object the Project Context Engine produces.
    It is stored in the generation context as the ``project_context``
    artefact.

    The Project Context is **read-only** for all downstream engines —
    no engine may modify it directly.  Any modification requires a
    dedicated engine.

    The context is the **single reference point** for all downstream
    engines.  Instead of re-reading the six upstream artefacts, every
    downstream engine reads the Project Context and uses the precomputed
    link indices to access any piece of information in O(1) time.

    Attributes:
        goal: The :class:`ProjectGoal` — the high-level project
            identity and primary goal.
        features: The list of :class:`FeatureSummary` objects.
        components: The list of :class:`ComponentSummary` objects.
        files: The list of :class:`FileSummary` objects.
        dependencies: The list of :class:`DependencySummary`
            objects.
        relationships: The list of :class:`RelationshipSummary`
            objects (normalised from all upstream artefacts).
        stages: The list of :class:`ExecutionStage` objects.
        links: The list of :class:`ContextLink` objects (the
            context graph edges).
        indices: The :class:`LinkIndices` — precomputed O(1)
            look-up tables.
        expansion_points: The list of :class:`ExpansionPoint`
            objects.
        provenance: The :class:`SourceProvenance` — traceability
            record.
        findings: The list of :class:`ContextFinding` objects
            produced during context building and validation.
        summary: A human-readable summary.
        notes: General notes about the context.
        warnings: Warnings produced during context building.
    """

    goal: ProjectGoal = field(default_factory=ProjectGoal)
    features: List[FeatureSummary] = field(default_factory=list)
    components: List[ComponentSummary] = field(default_factory=list)
    files: List[FileSummary] = field(default_factory=list)
    dependencies: List[DependencySummary] = field(default_factory=list)
    relationships: List[RelationshipSummary] = field(default_factory=list)
    stages: List[ExecutionStage] = field(default_factory=list)
    links: List[ContextLink] = field(default_factory=list)
    indices: LinkIndices = field(default_factory=LinkIndices)
    expansion_points: List[ExpansionPoint] = field(default_factory=list)
    provenance: SourceProvenance = field(default_factory=SourceProvenance)
    findings: List[ContextFinding] = field(default_factory=list)
    summary: str = ""
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # -- convenience -------------------------------------------------------#

    @property
    def feature_count(self) -> int:
        return len(self.features)

    @property
    def component_count(self) -> int:
        return len(self.components)

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def dependency_count(self) -> int:
        return len(self.dependencies)

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)

    @property
    def stage_count(self) -> int:
        return len(self.stages)

    @property
    def link_count(self) -> int:
        return len(self.links)

    @property
    def is_empty(self) -> bool:
        return (
            self.feature_count == 0
            and self.component_count == 0
            and self.file_count == 0
            and self.dependency_count == 0
        )

    @property
    def has_errors(self) -> bool:
        return any(
            f.severity == SEVERITY_ERROR for f in self.findings
        )

    @property
    def error_count(self) -> int:
        return sum(
            1 for f in self.findings if f.severity == SEVERITY_ERROR
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1 for f in self.findings if f.severity == SEVERITY_WARNING
        )

    # -- look-up helpers (O(n) but cached by caller) -----------------------#

    def get_feature(self, name: str) -> Optional[FeatureSummary]:
        for f in self.features:
            if f.name == name:
                return f
        return None

    def get_component(self, name: str) -> Optional[ComponentSummary]:
        for c in self.components:
            if c.name == name:
                return c
        return None

    def get_file(self, path: str) -> Optional[FileSummary]:
        for f in self.files:
            if f.path == path:
                return f
        return None

    def get_dependency(self, name: str) -> Optional[DependencySummary]:
        for d in self.dependencies:
            if d.name == name:
                return d
        return None

    def get_stage(self, name: str) -> Optional[ExecutionStage]:
        for s in self.stages:
            if s.name == name:
                return s
        return None

    # -- index-based O(1) look-ups -----------------------------------------#

    def components_for_feature(self, feature_name: str) -> List[str]:
        """Return the component names that implement a feature (O(1))."""
        return self.indices.feature_to_components.get(feature_name, [])

    def features_for_component(self, component_name: str) -> List[str]:
        """Return the feature names that a component belongs to (O(1))."""
        return self.indices.component_to_features.get(component_name, [])

    def files_for_component(self, component_name: str) -> List[str]:
        """Return the file paths that implement a component (O(1))."""
        return self.indices.component_to_files.get(component_name, [])

    def components_for_file(self, file_path: str) -> List[str]:
        """Return the component names that a file belongs to (O(1))."""
        return self.indices.file_to_components.get(file_path, [])

    def dependencies_for_file(self, file_path: str) -> List[str]:
        """Return the dependency names that a file requires (O(1))."""
        return self.indices.file_to_dependencies.get(file_path, [])

    def files_for_dependency(self, dependency_name: str) -> List[str]:
        """Return the file paths that require a dependency (O(1))."""
        return self.indices.dependency_to_files.get(dependency_name, [])

    def components_for_dependency(self, dependency_name: str) -> List[str]:
        """Return the component names that require a dependency (O(1))."""
        return self.indices.dependency_to_components.get(
            dependency_name, [],
        )

    def dependencies_for_component(self, component_name: str) -> List[str]:
        """Return the dependency names that a component requires (O(1))."""
        return self.indices.component_to_dependencies.get(
            component_name, [],
        )

    def stage_for_component(self, component_name: str) -> str:
        """Return the stage name for a component (O(1))."""
        return self.indices.component_to_stage.get(component_name, "")

    def stage_for_feature(self, feature_name: str) -> str:
        """Return the stage name for a feature (O(1))."""
        return self.indices.feature_to_stage.get(feature_name, "")

    def stage_for_file(self, file_path: str) -> str:
        """Return the stage name for a file (O(1))."""
        return self.indices.file_to_stage.get(file_path, "")

    def stage_for_dependency(self, dependency_name: str) -> str:
        """Return the stage name for a dependency (O(1))."""
        return self.indices.dependency_to_stage.get(dependency_name, "")

    # -- finding management -----------------------------------------------#

    def add_finding(
        self,
        severity: str,
        code: str,
        message: str,
        affected: str = "",
        resolution_hint: str = "",
        category: str = "validation",
    ) -> None:
        """Add a finding to the context."""
        self.findings.append(ContextFinding(
            severity=severity,
            code=code,
            message=message,
            affected=affected,
            resolution_hint=resolution_hint,
            category=category,
        ))
        if severity == SEVERITY_WARNING:
            self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal.to_dict(),
            "feature_count": self.feature_count,
            "component_count": self.component_count,
            "file_count": self.file_count,
            "dependency_count": self.dependency_count,
            "relationship_count": self.relationship_count,
            "stage_count": self.stage_count,
            "link_count": self.link_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "summary": self.summary,
            "notes": list(self.notes),
            "warnings": list(self.warnings),
            "features": [f.to_dict() for f in self.features],
            "components": [c.to_dict() for c in self.components],
            "files": [f.to_dict() for f in self.files],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "relationships": [r.to_dict() for r in self.relationships],
            "stages": [s.to_dict() for s in self.stages],
            "links": [l.to_dict() for l in self.links],
            "indices": self.indices.to_dict(),
            "expansion_points": [e.to_dict() for e in self.expansion_points],
            "provenance": self.provenance.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
        }


__all__ = [
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
    # Data model
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
    "ProjectContext",
]
