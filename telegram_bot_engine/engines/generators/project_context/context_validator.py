"""
Context validator (Specification 010).

The :class:`ContextValidator` validates the unified
:class:`ProjectContext` for internal consistency.  It checks that:

* **No features without components** — every feature has at least one
  component that implements it.
* **No components without files** — every component has at least one
  file that implements it (unless the component is a pure
  infrastructure component that has no files yet).
* **No files without responsibility** — every file has a
  ``source_component`` or a ``responsible_engine``.
* **No conflicting data** — no two features have the same name, no
  two components have the same name, no two files have the same path,
  no two dependencies have the same name.
* **No unknown elements** — every component referenced in a
  relationship exists, every file referenced in a relationship
  exists.
* **All stages have components** — every stage has at least one
  component (unless it is explicitly skippable).

The validator does **not** write code, create files, or make build
decisions.  It is a pure validation helper that produces
:class:`ContextFinding` objects.
"""

from __future__ import annotations

from typing import Dict, List, Set

from .context_data import (
    ProjectContext,
    ContextFinding,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SEVERITY_INFO,
)


class ContextValidator:
    """Validate the :class:`ProjectContext` for internal consistency.

    The validator is stateless.
    """

    def validate(self, context: ProjectContext) -> List[ContextFinding]:
        """Validate the context and return a list of findings.

        Findings with ``severity == SEVERITY_ERROR`` indicate
        inconsistencies that make the context unreliable for
        downstream engines.  Findings with
        ``severity == SEVERITY_WARNING`` indicate potential issues
        that downstream engines should be aware of.
        """
        findings: List[ContextFinding] = []

        findings.extend(self._check_duplicate_names(context))
        findings.extend(self._check_features_without_components(context))
        findings.extend(self._check_components_without_files(context))
        findings.extend(self._check_files_without_responsibility(context))
        findings.extend(self._check_unknown_elements_in_relationships(context))
        findings.extend(self._check_stages_without_components(context))
        findings.extend(self._check_orphaned_components(context))

        return findings

    # ------------------------------------------------------------------ #
    # Duplicate name check
    # ------------------------------------------------------------------ #

    def _check_duplicate_names(
        self, context: ProjectContext,
    ) -> List[ContextFinding]:
        """Check for duplicate feature, component, file, and dependency
        names.
        """
        findings: List[ContextFinding] = []

        # Duplicate feature names.
        seen: Set[str] = set()
        for f in context.features:
            if f.name in seen:
                findings.append(ContextFinding(
                    severity=SEVERITY_ERROR,
                    code="duplicate_feature_name",
                    message=(
                        f"Duplicate feature name '{f.name}'. "
                        f"Feature names must be unique."
                    ),
                    affected=f.name,
                    resolution_hint=(
                        "Rename one of the duplicate features."
                    ),
                    category="consistency",
                ))
            seen.add(f.name)

        # Duplicate component names.
        seen = set()
        for c in context.components:
            if c.name in seen:
                findings.append(ContextFinding(
                    severity=SEVERITY_ERROR,
                    code="duplicate_component_name",
                    message=(
                        f"Duplicate component name '{c.name}'. "
                        f"Component names must be unique."
                    ),
                    affected=c.name,
                    resolution_hint=(
                        "Rename one of the duplicate components."
                    ),
                    category="consistency",
                ))
            seen.add(c.name)

        # Duplicate file paths.
        seen = set()
        for f in context.files:
            if f.path in seen:
                findings.append(ContextFinding(
                    severity=SEVERITY_ERROR,
                    code="duplicate_file_path",
                    message=(
                        f"Duplicate file path '{f.path}'. "
                        f"File paths must be unique."
                    ),
                    affected=f.path,
                    resolution_hint=(
                        "Remove one of the duplicate files."
                    ),
                    category="consistency",
                ))
            seen.add(f.path)

        # Duplicate dependency names.
        seen = set()
        for d in context.dependencies:
            if d.name in seen:
                findings.append(ContextFinding(
                    severity=SEVERITY_ERROR,
                    code="duplicate_dependency_name",
                    message=(
                        f"Duplicate dependency name '{d.name}'. "
                        f"Dependency names must be unique."
                    ),
                    affected=d.name,
                    resolution_hint=(
                        "Merge or rename the duplicate dependencies."
                    ),
                    category="consistency",
                ))
            seen.add(d.name)

        return findings

    # ------------------------------------------------------------------ #
    # Features without components
    # ------------------------------------------------------------------ #

    def _check_features_without_components(
        self, context: ProjectContext,
    ) -> List[ContextFinding]:
        """Check for features that have no components implementing them.
        """
        findings: List[ContextFinding] = []
        for f in context.features:
            if not f.components:
                findings.append(ContextFinding(
                    severity=SEVERITY_WARNING,
                    code="feature_without_components",
                    message=(
                        f"Feature '{f.name}' has no components "
                        f"implementing it."
                    ),
                    affected=f.name,
                    resolution_hint=(
                        "Ensure the component detector detects "
                        "components for this feature."
                    ),
                    category="linking",
                ))
        return findings

    # ------------------------------------------------------------------ #
    # Components without files
    # ------------------------------------------------------------------ #

    def _check_components_without_files(
        self, context: ProjectContext,
    ) -> List[ContextFinding]:
        """Check for components that have no files implementing them.
        """
        findings: List[ContextFinding] = []
        for c in context.components:
            if not c.files:
                findings.append(ContextFinding(
                    severity=SEVERITY_WARNING,
                    code="component_without_files",
                    message=(
                        f"Component '{c.name}' has no files "
                        f"implementing it."
                    ),
                    affected=c.name,
                    resolution_hint=(
                        "Ensure the file planner plans files for "
                        "this component."
                    ),
                    category="linking",
                ))
        return findings

    # ------------------------------------------------------------------ #
    # Files without responsibility
    # ------------------------------------------------------------------ #

    def _check_files_without_responsibility(
        self, context: ProjectContext,
    ) -> List[ContextFinding]:
        """Check for files that have no source_component and no
        responsible_engine.
        """
        findings: List[ContextFinding] = []
        for f in context.files:
            if not f.source_component and not f.responsible_engine:
                findings.append(ContextFinding(
                    severity=SEVERITY_WARNING,
                    code="file_without_responsibility",
                    message=(
                        f"File '{f.path}' has no source component "
                        f"and no responsible engine."
                    ),
                    affected=f.path,
                    resolution_hint=(
                        "Assign this file to a component or "
                        "specify a responsible engine."
                    ),
                    category="linking",
                ))
        return findings

    # ------------------------------------------------------------------ #
    # Unknown elements in relationships
    # ------------------------------------------------------------------ #

    def _check_unknown_elements_in_relationships(
        self, context: ProjectContext,
    ) -> List[ContextFinding]:
        """Check for relationships that reference unknown elements.
        """
        findings: List[ContextFinding] = []

        known_components: Set[str] = {c.name for c in context.components}
        known_files: Set[str] = {f.path for f in context.files}
        known_deps: Set[str] = {d.name for d in context.dependencies}
        known_features: Set[str] = {f.name for f in context.features}
        known_all: Set[str] = (
            known_components | known_files | known_deps | known_features
        )

        for rel in context.relationships:
            if rel.source and rel.source not in known_all:
                findings.append(ContextFinding(
                    severity=SEVERITY_WARNING,
                    code="unknown_relationship_source",
                    message=(
                        f"Relationship source '{rel.source}' "
                        f"is not a known element."
                    ),
                    affected=rel.source,
                    resolution_hint=(
                        "Remove the relationship or add the "
                        "missing element."
                    ),
                    category="consistency",
                ))
            if rel.target and rel.target not in known_all:
                findings.append(ContextFinding(
                    severity=SEVERITY_WARNING,
                    code="unknown_relationship_target",
                    message=(
                        f"Relationship target '{rel.target}' "
                        f"is not a known element."
                    ),
                    affected=rel.target,
                    resolution_hint=(
                        "Remove the relationship or add the "
                        "missing element."
                    ),
                    category="consistency",
                ))

        return findings

    # ------------------------------------------------------------------ #
    # Stages without components
    # ------------------------------------------------------------------ #

    def _check_stages_without_components(
        self, context: ProjectContext,
    ) -> List[ContextFinding]:
        """Check for stages that have no components, files, or
        dependencies.
        """
        findings: List[ContextFinding] = []
        for stage in context.stages:
            if not stage.components and not stage.files and not stage.dependencies:
                findings.append(ContextFinding(
                    severity=SEVERITY_INFO,
                    code="empty_stage",
                    message=(
                        f"Stage '{stage.name}' (phase {stage.phase}) "
                        f"has no components, files, or dependencies."
                    ),
                    affected=stage.name,
                    resolution_hint=(
                        "This stage may be skippable or may "
                        "require components to be assigned."
                    ),
                    category="consistency",
                ))
        return findings

    # ------------------------------------------------------------------ #
    # Orphaned components
    # ------------------------------------------------------------------ #

    def _check_orphaned_components(
        self, context: ProjectContext,
    ) -> List[ContextFinding]:
        """Check for components that are not in any stage.
        """
        findings: List[ContextFinding] = []

        stage_components: Set[str] = set()
        for stage in context.stages:
            stage_components.update(stage.components)

        for c in context.components:
            if c.name not in stage_components and context.stages:
                findings.append(ContextFinding(
                    severity=SEVERITY_INFO,
                    code="orphaned_component",
                    message=(
                        f"Component '{c.name}' is not assigned to "
                        f"any execution stage."
                    ),
                    affected=c.name,
                    resolution_hint=(
                        "Assign this component to the appropriate "
                        "stage in the execution plan."
                    ),
                    category="consistency",
                ))

        return findings


__all__ = ["ContextValidator"]
