"""
Context assembler (Specification 010).

The :class:`ContextAssembler` merges the output of all six readers into
the unified :class:`ProjectContext`.  It is the "glue" that takes the
partial data from each reader and assembles the complete, coherent
context model.

The assembler does **not** write code, create files, or make build
decisions.  It performs the following operations:

1. **Merge features** — from the blueprint reader.
2. **Merge components** — from the registry reader.
3. **Merge files** — from the structure reader and the file plan
   reader (the file plan is the authoritative source; the structure
   map fills in any gaps).
4. **Merge dependencies** — from the dependency reader.
5. **Merge relationships** — from all readers (deduplicated).
6. **Merge stages** — from the blueprint reader (the execution plan
   phases), enriched with components, files, and dependencies.
7. **Merge expansion points** — from all readers (deduplicated).
8. **Merge findings** — from the validation and dependency readers.
9. **Build provenance** — from all the provenance partial dicts.
10. **Cross-link components and files** — populate the ``files`` list
    on each component and the ``components`` list on each feature.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from .context_data import (
    ProjectContext,
    ProjectGoal,
    FeatureSummary,
    ComponentSummary,
    FileSummary,
    DependencySummary,
    RelationshipSummary,
    ExecutionStage,
    ExpansionPoint,
    ContextFinding,
    ContextLink,
    SourceProvenance,
    SOURCE_BLUEPRINT,
    SOURCE_VALIDATION,
    SOURCE_STRUCTURE,
    SOURCE_COMPONENT_REGISTRY,
    SOURCE_FILE_PLAN,
    SOURCE_DEPENDENCY_REPORT,
    ALL_SOURCES,
)
from .blueprint_reader import BlueprintReader
from .validation_reader import ValidationReader
from .structure_reader import StructureReader
from .registry_reader import RegistryReader
from .file_plan_reader import FilePlanReader
from .dependency_reader import DependencyReader


class ContextAssembler:
    """Merge all readers' output into the unified :class:`ProjectContext`.

    The assembler is stateless — a new instance can be created for each
    call or a single instance can be reused.
    """

    def __init__(self) -> None:
        self._blueprint_reader = BlueprintReader()
        self._validation_reader = ValidationReader()
        self._structure_reader = StructureReader()
        self._registry_reader = RegistryReader()
        self._file_plan_reader = FilePlanReader()
        self._dependency_reader = DependencyReader()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def assemble(
        self,
        blueprint: Any,
        validation_report: Any,
        structure_map: Any,
        registry: Any,
        file_plan: Any,
        dependency_report: Any,
    ) -> ProjectContext:
        """Assemble the complete :class:`ProjectContext` from all six
        upstream artefacts.

        Parameters:
            blueprint: the :class:`ProjectBlueprint`.
            validation_report: the
                :class:`BlueprintValidationReport`.
            structure_map: the :class:`ProjectStructureMap`.
            registry: the :class:`ComponentRegistry`.
            file_plan: the :class:`FileGenerationPlan`.
            dependency_report: the
                :class:`DependencyResolutionReport`.

        Returns:
            A complete, populated :class:`ProjectContext`.
        """
        # -- Read each artefact ------------------------------------------ #
        bp_data = self._blueprint_reader.read(blueprint)
        val_data = self._validation_reader.read(validation_report)
        struct_data = self._structure_reader.read(structure_map)
        reg_data = self._registry_reader.read(registry)
        fp_data = self._file_plan_reader.read(file_plan)
        dep_data = self._dependency_reader.read(dependency_report)

        # -- Assemble the context ---------------------------------------- #
        context = ProjectContext()

        # Goal.
        context.goal = bp_data["goal"]

        # Features.
        context.features = bp_data["features"]

        # Components.
        context.components = reg_data["components"]

        # Files — merge from structure map and file plan.
        context.files = self._merge_files(
            struct_data["files"],
            fp_data["files"],
            struct_data.get("build_order_map", {}),
            fp_data.get("build_order_map", {}),
        )

        # Dependencies.
        context.dependencies = dep_data["dependencies"]

        # Relationships — merge from all sources, deduplicated.
        context.relationships = self._merge_relationships(
            bp_data["relationships"],
            struct_data["relationships"],
            reg_data["relationships"],
            fp_data["relationships"],
            dep_data["relationships"],
        )

        # Stages — from the blueprint, enriched.
        context.stages = self._enrich_stages(
            bp_data["stages"],
            context.components,
            context.files,
            context.dependencies,
        )

        # Expansion points — merge from all sources, deduplicated.
        context.expansion_points = self._merge_expansion_points(
            bp_data["expansion_points"],
            struct_data["expansion_points"],
            reg_data["expansion_points"],
            fp_data["expansion_points"],
        )

        # Findings — from validation and dependency readers.
        context.findings = self._merge_findings(
            val_data["findings"],
            dep_data["findings"],
        )

        # Provenance.
        context.provenance = self._build_provenance(
            bp_data, val_data, struct_data, reg_data, fp_data, dep_data,
        )

        # Cross-link features and components.
        self._cross_link_features_and_components(
            context.features, context.components,
        )

        # Cross-link components and files.
        self._cross_link_components_and_files(
            context.components, context.files,
        )

        # Cross-link components and dependencies.
        self._cross_link_components_and_dependencies(
            context.components, context.dependencies,
        )

        return context

    # ------------------------------------------------------------------ #
    # File merging
    # ------------------------------------------------------------------ #

    def _merge_files(
        self,
        struct_files: List[FileSummary],
        plan_files: List[FileSummary],
        struct_order_map: Dict[str, int],
        plan_order_map: Dict[str, int],
    ) -> List[FileSummary]:
        """Merge files from the structure map and the file plan.

        The file plan is the authoritative source for file metadata
        (purpose, depends_on, source_component, etc.).  The structure
        map fills in any files that the plan does not have.
        """
        merged: Dict[str, FileSummary] = {}

        # First, add all files from the file plan (authoritative).
        for f in plan_files:
            merged[f.path] = f

        # Then, add any files from the structure map that are not in
        # the plan.
        for f in struct_files:
            if f.path not in merged:
                merged[f.path] = f
            else:
                # Merge: if the plan entry is missing fields, fill
                # them from the structure entry.
                existing = merged[f.path]
                if not existing.reason_for_existence and f.reason_for_existence:
                    existing.reason_for_existence = f.reason_for_existence
                if not existing.source_component and f.source_component:
                    existing.source_component = f.source_component

        # Update build orders from the order maps.
        for path, f in merged.items():
            if path in plan_order_map:
                f.build_order = plan_order_map[path]
            elif path in struct_order_map:
                f.build_order = struct_order_map[path]

        return list(merged.values())

    # ------------------------------------------------------------------ #
    # Relationship merging
    # ------------------------------------------------------------------ #

    def _merge_relationships(
        self,
        *relationship_lists: List[RelationshipSummary],
    ) -> List[RelationshipSummary]:
        """Merge relationships from all sources, deduplicating by
        (source, target, kind).
        """
        seen: Set[tuple] = set()
        merged: List[RelationshipSummary] = []
        for rel_list in relationship_lists:
            for rel in rel_list:
                key = (rel.source, rel.target, rel.kind)
                if key not in seen:
                    seen.add(key)
                    merged.append(rel)
        return merged

    # ------------------------------------------------------------------ #
    # Stage enrichment
    # ------------------------------------------------------------------ #

    def _enrich_stages(
        self,
        base_stages: List[ExecutionStage],
        components: List[ComponentSummary],
        files: List[FileSummary],
        dependencies: List[DependencySummary],
    ) -> List[ExecutionStage]:
        """Enrich the execution stages with files and dependencies.

        The base stages from the blueprint already have the component
        names.  We add the files that belong to each stage (by matching
        the component → file links) and the dependencies that belong
        to each stage (by matching the component → dependency links).
        """
        # Build a component → files map.
        comp_to_files: Dict[str, List[str]] = {}
        for f in files:
            if f.source_component:
                comp_to_files.setdefault(f.source_component, []).append(f.path)

        # Build a component → dependencies map.
        comp_to_deps: Dict[str, List[str]] = {}
        for dep in dependencies:
            for comp_name in dep.source_components:
                comp_to_deps.setdefault(comp_name, []).append(dep.name)

        for stage in base_stages:
            stage_files: List[str] = []
            for comp_name in stage.components:
                stage_files.extend(comp_to_files.get(comp_name, []))
            stage.files = list(dict.fromkeys(stage_files))  # dedupe, preserve order

            stage_deps: List[str] = []
            for comp_name in stage.components:
                stage_deps.extend(comp_to_deps.get(comp_name, []))
            stage.dependencies = list(dict.fromkeys(stage_deps))

        return base_stages

    # ------------------------------------------------------------------ #
    # Expansion-point merging
    # ------------------------------------------------------------------ #

    def _merge_expansion_points(
        self,
        *ep_lists: List[ExpansionPoint],
    ) -> List[ExpansionPoint]:
        """Merge expansion points from all sources, deduplicating by
        area.
        """
        seen: Set[str] = set()
        merged: List[ExpansionPoint] = []
        for ep_list in ep_lists:
            for ep in ep_list:
                if ep.area not in seen:
                    seen.add(ep.area)
                    merged.append(ep)
        return merged

    # ------------------------------------------------------------------ #
    # Finding merging
    # ------------------------------------------------------------------ #

    def _merge_findings(
        self,
        *finding_lists: List[ContextFinding],
    ) -> List[ContextFinding]:
        """Merge findings from all sources."""
        merged: List[ContextFinding] = []
        for finding_list in finding_lists:
            merged.extend(finding_list)
        return merged

    # ------------------------------------------------------------------ #
    # Provenance
    # ------------------------------------------------------------------ #

    def _build_provenance(
        self,
        bp_data: Dict[str, Any],
        val_data: Dict[str, Any],
        struct_data: Dict[str, Any],
        reg_data: Dict[str, Any],
        fp_data: Dict[str, Any],
        dep_data: Dict[str, Any],
    ) -> SourceProvenance:
        """Build the source provenance from all the provenance partial
        dicts.
        """
        bp_partial = bp_data.get("provenance_partial", {})
        val_partial = val_data.get("provenance_partial", {})
        struct_partial = struct_data.get("provenance_partial", {})
        reg_partial = reg_data.get("provenance_partial", {})
        fp_partial = fp_data.get("provenance_partial", {})
        dep_partial = dep_data.get("provenance_partial", {})

        return SourceProvenance(
            blueprint_name=bp_data["goal"].name,
            validation_status=val_partial.get("validation_status", ""),
            structure_map_name=struct_partial.get("structure_map_name", ""),
            component_registry_name=reg_partial.get("component_registry_name", ""),
            file_plan_name=fp_partial.get("file_plan_name", ""),
            dependency_report_name=dep_partial.get("dependency_report_name", ""),
            all_sources_used=list(ALL_SOURCES),
        )

    # ------------------------------------------------------------------ #
    # Cross-linking
    # ------------------------------------------------------------------ #

    def _cross_link_features_and_components(
        self,
        features: List[FeatureSummary],
        components: List[ComponentSummary],
    ) -> None:
        """Populate the ``components`` list on each feature (from the
        feature's ``introduces_components``) and the ``source_feature``
        on each component.
        """
        # Build a component name → component map.
        comp_map: Dict[str, ComponentSummary] = {
            c.name: c for c in components
        }

        for feature in features:
            # The feature's components list comes from the blueprint
            # (introduces_components).  We also check if any component
            # in the registry has this feature as its source_feature.
            linked = set(feature.components)
            for comp in components:
                if comp.source_feature and comp.source_feature == feature.name:
                    linked.add(comp.name)
            feature.components = sorted(linked)

            # Update the component's source_feature if it was not set.
            for comp_name in feature.components:
                comp = comp_map.get(comp_name)
                if comp and not comp.source_feature:
                    comp.source_feature = feature.name

    def _cross_link_components_and_files(
        self,
        components: List[ComponentSummary],
        files: List[FileSummary],
    ) -> None:
        """Populate the ``files`` list on each component (from the
        file's ``source_component``).
        """
        # Build a component name → file paths map.
        comp_to_files: Dict[str, List[str]] = {}
        for f in files:
            if f.source_component:
                comp_to_files.setdefault(f.source_component, []).append(f.path)

        for comp in components:
            comp.files = list(
                dict.fromkeys(
                    comp_to_files.get(comp.name, [])
                )
            )

    def _cross_link_components_and_dependencies(
        self,
        components: List[ComponentSummary],
        dependencies: List[DependencySummary],
    ) -> None:
        """Populate the ``dependencies`` list on each component (from
        the dependency's ``source_components``).
        """
        # Build a component name → dependency names map.
        comp_to_deps: Dict[str, List[str]] = {}
        for dep in dependencies:
            for comp_name in dep.source_components:
                comp_to_deps.setdefault(comp_name, []).append(dep.name)

        for comp in components:
            comp.dependencies = list(
                dict.fromkeys(
                    comp_to_deps.get(comp.name, [])
                )
            )


__all__ = ["ContextAssembler"]
