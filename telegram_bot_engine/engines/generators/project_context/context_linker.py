"""
Context linker (Specification 010).

The :class:`ContextLinker` builds the precomputed O(1) look-up
indices that the :class:`ProjectContext` uses to traverse the context
graph in constant time.

The linker connects elements across the different layers of the
Project Context:

* **Feature → Component**: which components implement a feature.
* **Component → File**: which files implement a component.
* **File → Dependency**: which dependencies a file requires.
* **Dependency → Stage**: which stage a dependency belongs to.
* **Component → Stage**: which stage a component belongs to.
* **Feature → Stage**: which stage a feature belongs to.

The linker also produces the list of :class:`ContextLink` objects
that record every edge in the context graph, tagged with the
artefact it was derived from.

The linker does **not** write code, create files, or make build
decisions.  It is a pure index-building helper.
"""

from __future__ import annotations

from typing import Dict, List

from .context_data import (
    ProjectContext,
    LinkIndices,
    ContextLink,
    FeatureSummary,
    ComponentSummary,
    FileSummary,
    DependencySummary,
    ExecutionStage,
    LINK_FEATURE_TO_COMPONENT,
    LINK_COMPONENT_TO_FILE,
    LINK_FILE_TO_DEPENDENCY,
    LINK_DEPENDENCY_TO_STAGE,
    LINK_COMPONENT_TO_STAGE,
    LINK_FEATURE_TO_STAGE,
    SOURCE_BLUEPRINT,
    SOURCE_COMPONENT_REGISTRY,
    SOURCE_FILE_PLAN,
    SOURCE_DEPENDENCY_REPORT,
)


class ContextLinker:
    """Build the O(1) look-up indices for the context graph.

    The linker is stateless.
    """

    def link(self, context: ProjectContext) -> ProjectContext:
        """Build the link indices and the link list on the context.

        This method mutates the context in place (it sets the
        ``indices`` and ``links`` fields) and also returns the context
        for convenience.
        """
        # Build the link list first — it is the raw edge list.
        links = self._build_links(context)

        # Build the indices from the links and the direct associations.
        indices = self._build_indices(context, links)

        context.links = links
        context.indices = indices

        return context

    # ------------------------------------------------------------------ #
    # Link list
    # ------------------------------------------------------------------ #

    def _build_links(self, context: ProjectContext) -> List[ContextLink]:
        """Build the complete list of context links (edges in the
        context graph).
        """
        links: List[ContextLink] = []

        # Feature → Component links.
        for feature in context.features:
            for comp_name in feature.components:
                links.append(ContextLink(
                    source=feature.name,
                    target=comp_name,
                    kind=LINK_FEATURE_TO_COMPONENT,
                    source_artefact=SOURCE_BLUEPRINT,
                ))

        # Component → File links.
        for comp in context.components:
            for file_path in comp.files:
                links.append(ContextLink(
                    source=comp.name,
                    target=file_path,
                    kind=LINK_COMPONENT_TO_FILE,
                    source_artefact=SOURCE_COMPONENT_REGISTRY,
                ))

        # File → Dependency links (via the component).
        # A file belongs to a component, and the component requires
        # certain dependencies.  So the file "requires" the same
        # dependencies its component requires.
        comp_to_deps: Dict[str, List[str]] = {}
        for dep in context.dependencies:
            for comp_name in dep.source_components:
                comp_to_deps.setdefault(comp_name, []).append(dep.name)

        for comp in context.components:
            for file_path in comp.files:
                for dep_name in comp_to_deps.get(comp.name, []):
                    links.append(ContextLink(
                        source=file_path,
                        target=dep_name,
                        kind=LINK_FILE_TO_DEPENDENCY,
                        source_artefact=SOURCE_FILE_PLAN,
                    ))

        # Component → Stage links.
        comp_to_stage = self._build_component_to_stage(context)
        for comp_name, stage_name in comp_to_stage.items():
            links.append(ContextLink(
                source=comp_name,
                target=stage_name,
                kind=LINK_COMPONENT_TO_STAGE,
                source_artefact=SOURCE_BLUEPRINT,
            ))

        # Dependency → Stage links.
        dep_to_stage = self._build_dependency_to_stage(context, comp_to_stage)
        for dep_name, stage_name in dep_to_stage.items():
            links.append(ContextLink(
                source=dep_name,
                target=stage_name,
                kind=LINK_DEPENDENCY_TO_STAGE,
                source_artefact=SOURCE_DEPENDENCY_REPORT,
            ))

        # Feature → Stage links (via the component).
        for feature in context.features:
            stage_name = ""
            for comp_name in feature.components:
                if comp_name in comp_to_stage:
                    stage_name = comp_to_stage[comp_name]
                    break
            if stage_name:
                links.append(ContextLink(
                    source=feature.name,
                    target=stage_name,
                    kind=LINK_FEATURE_TO_STAGE,
                    source_artefact=SOURCE_BLUEPRINT,
                ))

        return links

    # ------------------------------------------------------------------ #
    # Indices
    # ------------------------------------------------------------------ #

    def _build_indices(
        self,
        context: ProjectContext,
        links: List[ContextLink],
    ) -> LinkIndices:
        """Build the O(1) look-up indices from the links and the
        direct associations.
        """
        indices = LinkIndices()

        # -- feature_to_components / component_to_features ---------------- #
        for feature in context.features:
            indices.feature_to_components[feature.name] = list(feature.components)
        for comp in context.components:
            for feature in context.features:
                if comp.name in feature.components:
                    indices.component_to_features.setdefault(
                        comp.name, [],
                    ).append(feature.name)

        # -- component_to_files / file_to_components --------------------- #
        for comp in context.components:
            indices.component_to_files[comp.name] = list(comp.files)
        for f in context.files:
            if f.source_component:
                indices.file_to_components.setdefault(
                    f.source_component, [],
                ).append(f.path)
            # Also, for every component that lists this file:
            for comp in context.components:
                if f.path in comp.files:
                    indices.file_to_components.setdefault(
                        comp.name, [],
                    ).append(f.path)

        # -- file_to_dependencies / dependency_to_files ------------------- #
        # A file requires the dependencies its component requires.
        comp_to_deps: Dict[str, List[str]] = {}
        for dep in context.dependencies:
            for comp_name in dep.source_components:
                comp_to_deps.setdefault(comp_name, []).append(dep.name)

        for comp in context.components:
            for file_path in comp.files:
                deps = comp_to_deps.get(comp.name, [])
                indices.file_to_dependencies[file_path] = list(deps)
                for dep_name in deps:
                    indices.dependency_to_files.setdefault(
                        dep_name, [],
                    ).append(file_path)

        # -- dependency_to_components / component_to_dependencies -------- #
        for dep in context.dependencies:
            indices.dependency_to_components[dep.name] = list(
                dep.source_components
            )
        for comp in context.components:
            indices.component_to_dependencies[comp.name] = list(
                comp_to_deps.get(comp.name, [])
            )

        # -- component_to_stage / feature_to_stage / file_to_stage /
        #    dependency_to_stage ----------------------------------------- #
        comp_to_stage = self._build_component_to_stage(context)
        indices.component_to_stage = dict(comp_to_stage)

        for feature in context.features:
            for comp_name in feature.components:
                if comp_name in comp_to_stage:
                    indices.feature_to_stage[feature.name] = (
                        comp_to_stage[comp_name]
                    )
                    break

        for f in context.files:
            if f.source_component and f.source_component in comp_to_stage:
                indices.file_to_stage[f.path] = comp_to_stage[
                    f.source_component
                ]

        dep_to_stage = self._build_dependency_to_stage(context, comp_to_stage)
        indices.dependency_to_stage = dict(dep_to_stage)

        return indices

    # ------------------------------------------------------------------ #
    # Stage mapping helpers
    # ------------------------------------------------------------------ #

    def _build_component_to_stage(
        self, context: ProjectContext,
    ) -> Dict[str, str]:
        """Build a component name → stage name map from the execution
        stages.
        """
        comp_to_stage: Dict[str, str] = {}
        for stage in context.stages:
            for comp_name in stage.components:
                comp_to_stage[comp_name] = stage.name
        return comp_to_stage

    def _build_dependency_to_stage(
        self,
        context: ProjectContext,
        comp_to_stage: Dict[str, str],
    ) -> Dict[str, str]:
        """Build a dependency name → stage name map.

        A dependency belongs to the same stage as the components that
        require it.  When a dependency is required by components in
        multiple stages, it is assigned to the earliest (lowest phase)
        stage.
        """
        dep_to_stage: Dict[str, str] = {}

        # Build a stage name → phase map for sorting.
        stage_phase: Dict[str, int] = {
            s.name: s.phase for s in context.stages
        }

        for dep in context.dependencies:
            best_stage = ""
            best_phase = 9999
            for comp_name in dep.source_components:
                stage_name = comp_to_stage.get(comp_name, "")
                if stage_name:
                    phase = stage_phase.get(stage_name, 9999)
                    if phase < best_phase:
                        best_phase = phase
                        best_stage = stage_name
            if best_stage:
                dep_to_stage[dep.name] = best_stage

        return dep_to_stage


__all__ = ["ContextLinker"]
