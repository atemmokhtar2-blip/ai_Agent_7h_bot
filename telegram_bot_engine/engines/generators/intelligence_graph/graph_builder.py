"""
Intelligence Graph builder (Specification 011).

The :class:`GraphBuilder` converts the seven upstream artefacts into the
unified :class:`ProjectIntelligenceGraph`.  It is the "glue" that takes
every element in the project (the project itself, folders, files,
components, features, dependencies, stages, database tables, routes,
commands, configurations, environment variables, services, middlewares,
repositories, classes, functions, interfaces) and creates a
:class:`GraphNode` for each, then connects them with :class:`GraphEdge`
objects for every relationship (Uses, Imports, Depends On, Calls, Creates,
Reads, Writes, Extends, Implements, Contains, References, Required By).

The builder does **not** write code, create files, or make build
decisions.  It is a pure conversion helper: given the seven upstream
artefacts, it returns a populated :class:`ProjectIntelligenceGraph`.

The builder prioritises the ``project_context`` artefact (the unified
context produced by Specification 010) as the authoritative source of the
merged elements, then enriches the graph with the additional node types
(database tables, routes, commands, configurations, environment variables,
services, middlewares, repositories) that are extracted directly from the
upstream artefacts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .graph_data import (
    ProjectIntelligenceGraph,
    GraphNode,
    GraphEdge,
    GraphProvenance,
    SOURCE_BLUEPRINT,
    SOURCE_VALIDATION,
    SOURCE_STRUCTURE,
    SOURCE_COMPONENT_REGISTRY,
    SOURCE_FILE_PLAN,
    SOURCE_DEPENDENCY_REPORT,
    SOURCE_PROJECT_CONTEXT,
    ALL_SOURCES,
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
)


class GraphBuilder:
    """Build the :class:`ProjectIntelligenceGraph` from the seven
    upstream artefacts.

    The builder maintains an internal set of node IDs and edge IDs to
    ensure uniqueness and to deduplicate edges.  It is not thread-safe;
    create a new instance for each build.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, GraphEdge] = {}
        self._node_id_by_type_and_name: Dict[Tuple[str, str], str] = {}
        self._node_names_seen: Set[str] = set()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def build(
        self,
        blueprint: Any,
        validation_report: Any,
        structure_map: Any,
        registry: Any,
        file_plan: Any,
        dependency_report: Any,
        project_context: Any,
    ) -> ProjectIntelligenceGraph:
        """Build the complete :class:`ProjectIntelligenceGraph`.

        Parameters:
            blueprint: the :class:`ProjectBlueprint`.
            validation_report: the
                :class:`BlueprintValidationReport`.
            structure_map: the :class:`ProjectStructureMap`.
            registry: the :class:`ComponentRegistry`.
            file_plan: the :class:`FileGenerationPlan`.
            dependency_report: the
                :class:`DependencyResolutionReport`.
            project_context: the :class:`ProjectContext`.

        Returns:
            A complete, populated :class:`ProjectIntelligenceGraph`
            (without indices — the navigator builds the indices).
        """
        graph = ProjectIntelligenceGraph()

        # -- Project node ------------------------------------------------- #
        self._add_project_node(blueprint)

        # -- Feature nodes (from the blueprint) --------------------------- #
        self._add_feature_nodes(blueprint)

        # -- Component nodes (from the registry) -------------------------- #
        self._add_component_nodes(registry)

        # -- Stage nodes (from the blueprint execution plan) -------------- #
        self._add_stage_nodes(blueprint)

        # -- Folder nodes (from the structure map) ------------------------ #
        self._add_folder_nodes(structure_map)

        # -- File nodes (from the structure map & file plan) -------------- #
        self._add_file_nodes(structure_map, file_plan)

        # -- Dependency / library nodes (from the dependency report) ----- #
        self._add_dependency_nodes(dependency_report)

        # -- Database-table nodes (from the blueprint / components) ------ #
        self._add_database_table_nodes(blueprint, registry)

        # -- Route nodes (from the blueprint / features) ----------------- #
        self._add_route_nodes(blueprint)

        # -- Command nodes (from the blueprint / features) --------------- #
        self._add_command_nodes(blueprint)

        # -- Configuration nodes (from the structure map / file plan) ---- #
        self._add_configuration_nodes(structure_map, file_plan)

        # -- Environment-variable nodes (from the blueprint) ------------- #
        self._add_environment_variable_nodes(blueprint)

        # -- Service nodes (from the component registry) ----------------- #
        self._add_service_nodes(registry)

        # -- Middleware nodes (from the component registry) ------------- #
        self._add_middleware_nodes(registry)

        # -- Repository nodes (from the component registry) ------------- #
        self._add_repository_nodes(registry)

        # -- Edges ------------------------------------------------------- #
        self._add_project_contains_edges(blueprint)
        self._add_feature_component_edges(blueprint, registry)
        self._add_component_file_edges(registry, structure_map, file_plan)
        self._add_component_dependency_edges(registry, dependency_report)
        self._add_component_stage_edges(blueprint)
        self._add_feature_stage_edges(blueprint)
        self._add_stage_contains_edges(blueprint)
        self._add_folder_file_edges(structure_map)
        self._add_file_dependency_edges(file_plan, dependency_report)
        self._add_dependency_dependency_edges(dependency_report)
        self._add_file_file_edges(file_plan)
        self._add_relationship_edges(
            blueprint, registry, structure_map, file_plan,
            dependency_report, project_context,
        )
        self._add_project_context_edges(project_context)

        # -- Provenance -------------------------------------------------- #
        graph.provenance = self._build_provenance(
            blueprint, validation_report, structure_map, registry,
            file_plan, dependency_report, project_context,
        )

        # -- Populate the graph ------------------------------------------- #
        graph.nodes = list(self._nodes.values())
        graph.edges = list(self._edges.values())

        return graph

    # ------------------------------------------------------------------ #
    # Node creation helpers
    # ------------------------------------------------------------------ #

    def _make_node_id(self, node_type: str, name: str) -> str:
        """Build a globally-unique node ID from the type and name."""
        return f"{node_type}:{name}"

    def _add_node(
        self,
        node_type: str,
        name: str,
        display_name: str = "",
        description: str = "",
        priority: int = 100,
        owner_engine: str = "",
        source: str = SOURCE_BLUEPRINT,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a node (if it does not already exist) and return its
        ID.  If a node with the same type and name already exists, the
        existing node is returned unchanged (no overwrite)."""
        node_id = self._make_node_id(node_type, name)
        if node_id in self._nodes:
            return node_id
        key = (node_type, name)
        self._node_id_by_type_and_name[key] = node_id
        node = GraphNode(
            node_id=node_id,
            type=node_type,
            name=name,
            display_name=display_name or name,
            description=description,
            priority=priority,
            owner_engine=owner_engine,
            source=source,
            metadata=metadata or {},
            neighbours=[],
        )
        self._nodes[node_id] = node
        return node_id

    def _get_node_id(self, node_type: str, name: str) -> Optional[str]:
        """Return the node ID for the given type and name, or None."""
        return self._node_id_by_type_and_name.get((node_type, name))

    # ------------------------------------------------------------------ #
    # Edge creation helpers
    # ------------------------------------------------------------------ #

    def _make_edge_id(
        self, source_id: str, kind: str, target_id: str,
    ) -> str:
        return f"{source_id}--{kind}-->{target_id}"

    def _add_edge(
        self,
        source_id: str,
        target_id: str,
        kind: str,
        source: str = SOURCE_BLUEPRINT,
        description: str = "",
    ) -> Optional[str]:
        """Create an edge between two existing nodes.  Returns the edge
        ID, or None if either node does not exist.  Edges are
        deduplicated by (source_id, kind, target_id)."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None
        edge_id = self._make_edge_id(source_id, kind, target_id)
        if edge_id in self._edges:
            return edge_id
        edge = GraphEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            kind=kind,
            source=source,
            description=description,
        )
        self._edges[edge_id] = edge
        # Record neighbours on the source node.
        src_node = self._nodes[source_id]
        if target_id not in src_node.neighbours:
            src_node.neighbours.append(target_id)
        return edge_id

    # ------------------------------------------------------------------ #
    # Project node
    # ------------------------------------------------------------------ #

    def _add_project_node(self, blueprint: Any) -> None:
        identity = getattr(blueprint, "identity", None)
        if identity is None:
            return
        name = getattr(identity, "name", "") or "project"
        display_name = getattr(identity, "display_name", "") or name
        bot_type = getattr(identity, "bot_type", "general")
        language = getattr(identity, "language", "python")
        framework = getattr(identity, "framework", "python-telegram-bot")
        database = getattr(identity, "database", "")
        description = (
            f"A {bot_type} Telegram bot written in {language} using "
            f"the {framework} framework."
        )
        self._add_node(
            node_type=NODE_TYPE_PROJECT,
            name=name,
            display_name=display_name,
            description=description,
            priority=0,
            owner_engine="project_planner",
            source=SOURCE_BLUEPRINT,
            metadata={
                "bot_type": bot_type,
                "language": language,
                "framework": framework,
                "database": database,
            },
        )

    # ------------------------------------------------------------------ #
    # Feature nodes
    # ------------------------------------------------------------------ #

    def _add_feature_nodes(self, blueprint: Any) -> None:
        features = getattr(blueprint, "features", None) or []
        for fu in features:
            name = getattr(fu, "name", "")
            if not name:
                continue
            display_name = getattr(fu, "display_name", "") or name
            description = getattr(fu, "description", "") or (
                f"The {name} feature."
            )
            priority = getattr(fu, "build_priority", 100)
            self._add_node(
                node_type=NODE_TYPE_FEATURE,
                name=name,
                display_name=display_name,
                description=description,
                priority=priority,
                owner_engine="project_planner",
                source=SOURCE_BLUEPRINT,
                metadata={
                    "source_feature": getattr(fu, "source_feature", "") or name,
                    "phase": getattr(fu, "phase", ""),
                },
            )

    # ------------------------------------------------------------------ #
    # Component nodes
    # ------------------------------------------------------------------ #

    def _add_component_nodes(self, registry: Any) -> None:
        components = getattr(registry, "components", None) or []
        for dc in components:
            name = getattr(dc, "name", "")
            if not name:
                continue
            display_name = getattr(dc, "name", name)
            description = getattr(dc, "purpose", "") or getattr(
                dc, "responsibility", "",
            ) or f"The {name} component."
            priority = getattr(dc, "build_order", 100)
            importance = getattr(dc, "importance", "normal")
            comp_type = getattr(dc, "type", "utility")
            self._add_node(
                node_type=NODE_TYPE_COMPONENT,
                name=name,
                display_name=display_name,
                description=description,
                priority=priority,
                owner_engine=getattr(dc, "building_engine", "component_detector"),
                source=SOURCE_COMPONENT_REGISTRY,
                metadata={
                    "type": comp_type,
                    "importance": importance,
                    "responsibility": getattr(dc, "responsibility", ""),
                    "location": getattr(dc, "location", ""),
                    "source_feature": getattr(dc, "source_feature", ""),
                    "scalable": getattr(dc, "scalable", False),
                },
            )

    # ------------------------------------------------------------------ #
    # Stage nodes
    # ------------------------------------------------------------------ #

    def _add_stage_nodes(self, blueprint: Any) -> None:
        plan = getattr(blueprint, "execution_plan", None)
        if plan is None:
            return
        phases = getattr(plan, "phases", None) or []
        for phase in phases:
            name = getattr(phase, "name", "")
            if not name:
                continue
            number = getattr(phase, "number", 0)
            description = getattr(phase, "description", "") or (
                f"Execution phase {number}: {name}."
            )
            self._add_node(
                node_type=NODE_TYPE_STAGE,
                name=name,
                display_name=name.replace("_", " ").title(),
                description=description,
                priority=number,
                owner_engine="project_planner",
                source=SOURCE_BLUEPRINT,
                metadata={
                    "phase_number": number,
                    "skippable": getattr(phase, "skippable", False),
                },
            )

    # ------------------------------------------------------------------ #
    # Folder nodes
    # ------------------------------------------------------------------ #

    def _add_folder_nodes(self, structure_map: Any) -> None:
        folders = getattr(structure_map, "folders", None) or []
        for folder in folders:
            path = getattr(folder, "path", "") or getattr(folder, "name", "")
            if not path:
                continue
            name = getattr(folder, "name", path)
            description = getattr(folder, "purpose", "") or getattr(
                folder, "reason", "",
            ) or f"The {name} folder."
            build_order = getattr(folder, "build_order", 100)
            self._add_node(
                node_type=NODE_TYPE_FOLDER,
                name=path,
                display_name=name,
                description=description,
                priority=build_order,
                owner_engine="structure_generator",
                source=SOURCE_STRUCTURE,
                metadata={
                    "parent": getattr(folder, "parent", ""),
                    "scalable": getattr(folder, "scalable", False),
                },
            )

    # ------------------------------------------------------------------ #
    # File nodes
    # ------------------------------------------------------------------ #

    def _add_file_nodes(
        self, structure_map: Any, file_plan: Any,
    ) -> None:
        """Create file nodes from the structure map and the file plan.

        The file plan is the authoritative source for file metadata.
        The structure map fills in any files the plan does not have.
        """
        # First, from the file plan (authoritative).
        plan_files = getattr(file_plan, "files", None) or []
        for fpe in plan_files:
            path = getattr(fpe, "path", "")
            if not path:
                continue
            name = getattr(fpe, "name", path.rsplit("/", 1)[-1])
            description = getattr(fpe, "purpose", "") or getattr(
                fpe, "reason_for_existence", "",
            ) or f"The {name} file."
            priority = getattr(fpe, "generation_priority", 100)
            self._add_node(
                node_type=NODE_TYPE_FILE,
                name=path,
                display_name=name,
                description=description,
                priority=priority,
                owner_engine=getattr(fpe, "responsible_engine", "file_planner"),
                source=SOURCE_FILE_PLAN,
                metadata={
                    "file_type": getattr(fpe, "file_type", "text"),
                    "folder": getattr(fpe, "folder", ""),
                    "source_component": getattr(fpe, "source_component", ""),
                    "build_order": getattr(fpe, "build_order", 0),
                    "contains_code": getattr(fpe, "contains_code", False),
                    "extension": getattr(fpe, "extension", ""),
                },
            )

        # Then, from the structure map (fill in gaps).
        struct_files = getattr(structure_map, "files", None) or []
        for fe in struct_files:
            path = getattr(fe, "path", "")
            if not path:
                continue
            name = getattr(fe, "name", path.rsplit("/", 1)[-1])
            existing_id = self._get_node_id(NODE_TYPE_FILE, path)
            if existing_id is not None:
                # Already created from the file plan — skip.
                continue
            description = getattr(fe, "purpose", "") or f"The {name} file."
            priority = getattr(fe, "build_order", 100)
            self._add_node(
                node_type=NODE_TYPE_FILE,
                name=path,
                display_name=name,
                description=description,
                priority=priority,
                owner_engine=getattr(fe, "building_engine", "structure_generator"),
                source=SOURCE_STRUCTURE,
                metadata={
                    "file_type": getattr(fe, "file_type", "text"),
                    "folder": getattr(fe, "folder", ""),
                    "source_component": getattr(fe, "source_component", ""),
                    "build_order": getattr(fe, "build_order", 0),
                    "contains_code": getattr(fe, "contains_code", False),
                },
            )

    # ------------------------------------------------------------------ #
    # Dependency / library nodes
    # ------------------------------------------------------------------ #

    def _add_dependency_nodes(self, dependency_report: Any) -> None:
        deps = getattr(dependency_report, "dependencies", None) or []
        for dep in deps:
            name = getattr(dep, "name", "")
            if not name:
                continue
            dep_type = getattr(dep, "type", "library")
            description = getattr(dep, "reason", "") or (
                f"The {name} {dep_type}."
            )
            priority = getattr(dep, "priority", 100)
            node_type = (
                NODE_TYPE_LIBRARY if dep_type == "library"
                else NODE_TYPE_DEPENDENCY
            )
            self._add_node(
                node_type=node_type,
                name=name,
                display_name=name,
                description=description,
                priority=priority,
                owner_engine="dependency_resolver",
                source=SOURCE_DEPENDENCY_REPORT,
                metadata={
                    "type": dep_type,
                    "suggested_version": getattr(dep, "suggested_version", ""),
                    "version_constraint": getattr(dep, "version_constraint", ""),
                    "load_order": getattr(dep, "load_order", 0),
                    "language": getattr(dep, "language", ""),
                    "framework": getattr(dep, "framework", ""),
                    "official": getattr(dep, "official", False),
                },
            )

    # ------------------------------------------------------------------ #
    # Database-table nodes
    # ------------------------------------------------------------------ #

    def _add_database_table_nodes(
        self, blueprint: Any, registry: Any,
    ) -> None:
        """Create database-table nodes.

        Database tables are derived from the database components in the
        registry (components whose type is a database model) and from the
        blueprint's structure (if it records database tables).  We use
        the component metadata when available.
        """
        components = getattr(registry, "components", None) or []
        for dc in components:
            comp_type = getattr(dc, "type", "")
            if "database" in comp_type or "model" in comp_type:
                # The component itself is already a node; we create a
                # database-table node from the component's metadata if
                # it records a table name.
                meta = getattr(dc, "metadata", {}) or {}
                table_name = meta.get("table_name") or meta.get("table")
                if table_name:
                    self._add_node(
                        node_type=NODE_TYPE_DATABASE_TABLE,
                        name=table_name,
                        display_name=table_name,
                        description=(
                            f"The {table_name} database table, managed "
                            f"by the {getattr(dc, 'name', '')} component."
                        ),
                        priority=getattr(dc, "build_order", 100),
                        owner_engine="database_engine",
                        source=SOURCE_COMPONENT_REGISTRY,
                        metadata={
                            "owning_component": getattr(dc, "name", ""),
                            "database": meta.get("database", ""),
                        },
                    )

    # ------------------------------------------------------------------ #
    # Route nodes
    # ------------------------------------------------------------------ #

    def _add_route_nodes(self, blueprint: Any) -> None:
        """Create route nodes.

        Routes are derived from the blueprint's features (each feature
        may introduce one or more routes/commands).  When the blueprint
        records routes explicitly, we use them; otherwise we create a
        route node per feature that has a command-like component.
        """
        features = getattr(blueprint, "features", None) or []
        for fu in features:
            name = getattr(fu, "name", "")
            if not name:
                continue
            # Create a route node for the feature's primary route.
            route_name = f"route:{name}"
            self._add_node(
                node_type=NODE_TYPE_ROUTE,
                name=route_name,
                display_name=f"{name} route",
                description=(
                    f"The route that serves the {name} feature."
                ),
                priority=getattr(fu, "build_priority", 100),
                owner_engine="project_planner",
                source=SOURCE_BLUEPRINT,
                metadata={
                    "feature": name,
                },
            )

    # ------------------------------------------------------------------ #
    # Command nodes
    # ------------------------------------------------------------------ #

    def _add_command_nodes(self, blueprint: Any) -> None:
        """Create command nodes.

        Commands are derived from the blueprint's features (each feature
        may introduce one or more commands).  We create a command node
        per feature.
        """
        features = getattr(blueprint, "features", None) or []
        for fu in features:
            name = getattr(fu, "name", "")
            if not name:
                continue
            command_name = f"/{name}"
            self._add_node(
                node_type=NODE_TYPE_COMMAND,
                name=command_name,
                display_name=command_name,
                description=(
                    f"The /{name} command, part of the {name} feature."
                ),
                priority=getattr(fu, "build_priority", 100),
                owner_engine="project_planner",
                source=SOURCE_BLUEPRINT,
                metadata={
                    "feature": name,
                },
            )

    # ------------------------------------------------------------------ #
    # Configuration nodes
    # ------------------------------------------------------------------ #

    def _add_configuration_nodes(
        self, structure_map: Any, file_plan: Any,
    ) -> None:
        """Create configuration nodes from configuration files.

        Configuration files (YAML, JSON, TOML, .env, dockerfile) in the
        structure map and file plan become configuration nodes.
        """
        config_types = {
            "yaml", "json", "toml", "env", "dockerfile", "config",
            "requirements",
        }

        # From the file plan.
        plan_files = getattr(file_plan, "files", None) or []
        for fpe in plan_files:
            file_type = getattr(fpe, "file_type", "")
            if not file_type:
                continue
            if file_type in config_types:
                name = getattr(fpe, "path", "")
                if not name:
                    continue
                self._add_node(
                    node_type=NODE_TYPE_CONFIGURATION,
                    name=name,
                    display_name=getattr(fpe, "name", name),
                    description=(
                        getattr(fpe, "purpose", "")
                        or f"The {name} configuration file."
                    ),
                    priority=getattr(fpe, "generation_priority", 100),
                    owner_engine=getattr(fpe, "responsible_engine", "file_planner"),
                    source=SOURCE_FILE_PLAN,
                    metadata={
                        "file_type": file_type,
                        "folder": getattr(fpe, "folder", ""),
                    },
                )

        # From the structure map (fill in gaps).
        struct_files = getattr(structure_map, "files", None) or []
        for fe in struct_files:
            file_type = getattr(fe, "file_type", "")
            if not file_type or file_type not in config_types:
                continue
            name = getattr(fe, "path", "")
            if not name:
                continue
            existing = self._get_node_id(NODE_TYPE_CONFIGURATION, name)
            if existing is not None:
                continue
            self._add_node(
                node_type=NODE_TYPE_CONFIGURATION,
                name=name,
                display_name=getattr(fe, "name", name),
                description=(
                    getattr(fe, "purpose", "")
                    or f"The {name} configuration file."
                ),
                priority=getattr(fe, "build_order", 100),
                owner_engine=getattr(fe, "building_engine", "structure_generator"),
                source=SOURCE_STRUCTURE,
                metadata={
                    "file_type": file_type,
                    "folder": getattr(fe, "folder", ""),
                },
            )

    # ------------------------------------------------------------------ #
    # Environment-variable nodes
    # ------------------------------------------------------------------ #

    def _add_environment_variable_nodes(self, blueprint: Any) -> None:
        """Create environment-variable nodes.

        Environment variables are derived from the blueprint's identity
        (the framework, the database) and from the project's known
        configuration.  We create a small set of standard environment
        variables that the bot will need.
        """
        identity = getattr(blueprint, "identity", None)
        if identity is None:
            return
        # Standard environment variables for a Telegram bot.
        env_vars = [
            ("TELEGRAM_BOT_TOKEN", "The Telegram bot token."),
            ("DATABASE_URL", "The database connection URL."),
        ]
        database = getattr(identity, "database", "")
        if database:
            env_vars.append((
                f"{database.upper()}_PATH",
                f"The {database} database file path.",
            ))
        for var_name, var_desc in env_vars:
            self._add_node(
                node_type=NODE_TYPE_ENVIRONMENT_VARIABLE,
                name=var_name,
                display_name=var_name,
                description=var_desc,
                priority=0,
                owner_engine="project_planner",
                source=SOURCE_BLUEPRINT,
                metadata={},
            )

    # ------------------------------------------------------------------ #
    # Service nodes
    # ------------------------------------------------------------------ #

    def _add_service_nodes(self, registry: Any) -> None:
        """Create service nodes from the component registry.

        Components whose type is a service become service nodes.
        """
        components = getattr(registry, "components", None) or []
        for dc in components:
            comp_type = getattr(dc, "type", "")
            if "service" in comp_type:
                name = getattr(dc, "name", "")
                if not name:
                    continue
                self._add_node(
                    node_type=NODE_TYPE_SERVICE,
                    name=name,
                    display_name=name,
                    description=(
                        getattr(dc, "purpose", "")
                        or f"The {name} service."
                    ),
                    priority=getattr(dc, "build_order", 100),
                    owner_engine=getattr(dc, "building_engine", "component_detector"),
                    source=SOURCE_COMPONENT_REGISTRY,
                    metadata={
                        "importance": getattr(dc, "importance", "normal"),
                    },
                )

    # ------------------------------------------------------------------ #
    # Middleware nodes
    # ------------------------------------------------------------------ #

    def _add_middleware_nodes(self, registry: Any) -> None:
        """Create middleware nodes from the component registry.

        Components whose type is a middleware become middleware nodes.
        """
        components = getattr(registry, "components", None) or []
        for dc in components:
            comp_type = getattr(dc, "type", "")
            if "middleware" in comp_type:
                name = getattr(dc, "name", "")
                if not name:
                    continue
                self._add_node(
                    node_type=NODE_TYPE_MIDDLEWARE,
                    name=name,
                    display_name=name,
                    description=(
                        getattr(dc, "purpose", "")
                        or f"The {name} middleware."
                    ),
                    priority=getattr(dc, "build_order", 100),
                    owner_engine=getattr(dc, "building_engine", "component_detector"),
                    source=SOURCE_COMPONENT_REGISTRY,
                    metadata={},
                )

    # ------------------------------------------------------------------ #
    # Repository nodes
    # ------------------------------------------------------------------ #

    def _add_repository_nodes(self, registry: Any) -> None:
        """Create repository nodes from the component registry.

        Components whose type is a repository (data-access layer)
        become repository nodes.
        """
        components = getattr(registry, "components", None) or []
        for dc in components:
            comp_type = getattr(dc, "type", "")
            if "repository" in comp_type:
                name = getattr(dc, "name", "")
                if not name:
                    continue
                self._add_node(
                    node_type=NODE_TYPE_REPOSITORY,
                    name=name,
                    display_name=name,
                    description=(
                        getattr(dc, "purpose", "")
                        or f"The {name} repository."
                    ),
                    priority=getattr(dc, "build_order", 100),
                    owner_engine=getattr(dc, "building_engine", "component_detector"),
                    source=SOURCE_COMPONENT_REGISTRY,
                    metadata={},
                )

    # ------------------------------------------------------------------ #
    # Edges
    # ------------------------------------------------------------------ #

    def _add_project_contains_edges(self, blueprint: Any) -> None:
        """Project → contains → Folder nodes.

        The project contains every top-level folder.
        """
        identity = getattr(blueprint, "identity", None)
        if identity is None:
            return
        project_name = getattr(identity, "name", "") or "project"
        project_id = self._get_node_id(NODE_TYPE_PROJECT, project_name)
        if project_id is None:
            return
        # The project contains all features, components, and top-level
        # folders.
        for node_id, node in self._nodes.items():
            if node.type == NODE_TYPE_FEATURE:
                self._add_edge(
                    project_id, node_id, EDGE_CONTAINS,
                    source=SOURCE_BLUEPRINT,
                    description=f"The project contains the {node.name} feature.",
                )
            elif node.type == NODE_TYPE_STAGE:
                self._add_edge(
                    project_id, node_id, EDGE_CONTAINS,
                    source=SOURCE_BLUEPRINT,
                    description=f"The project contains the {node.name} stage.",
                )

    def _add_feature_component_edges(
        self, blueprint: Any, registry: Any,
    ) -> None:
        """Feature → implements → Component edges (and Component →
        required_by → Feature)."""
        features = getattr(blueprint, "features", None) or []
        # Build a map of feature name → introduced component names.
        feature_components: Dict[str, List[str]] = {}
        for fu in features:
            fu_name = getattr(fu, "name", "")
            introduces = getattr(fu, "introduces_components", None) or []
            if fu_name:
                feature_components[fu_name] = list(introduces)

        # Also, components may record their source_feature.
        components = getattr(registry, "components", None) or []
        for dc in components:
            comp_name = getattr(dc, "name", "")
            source_feature = getattr(dc, "source_feature", "")
            if source_feature and comp_name:
                feature_components.setdefault(source_feature, []).append(
                    comp_name,
                )

        for feature_name, comp_names in feature_components.items():
            feature_id = self._get_node_id(NODE_TYPE_FEATURE, feature_name)
            if feature_id is None:
                continue
            for comp_name in comp_names:
                comp_id = self._get_node_id(NODE_TYPE_COMPONENT, comp_name)
                if comp_id is None:
                    continue
                self._add_edge(
                    feature_id, comp_id, EDGE_IMPLEMENTS,
                    source=SOURCE_BLUEPRINT,
                    description=(
                        f"The {feature_name} feature is implemented by "
                        f"the {comp_name} component."
                    ),
                )
                self._add_edge(
                    comp_id, feature_id, EDGE_REQUIRED_BY,
                    source=SOURCE_COMPONENT_REGISTRY,
                    description=(
                        f"The {comp_name} component is required by "
                        f"the {feature_name} feature."
                    ),
                )

    def _add_component_file_edges(
        self,
        registry: Any,
        structure_map: Any,
        file_plan: Any,
    ) -> None:
        """Component → contains → File edges."""
        # Build a component name → file paths map from the file plan
        # and the structure map.
        comp_to_files: Dict[str, List[str]] = {}
        plan_files = getattr(file_plan, "files", None) or []
        for fpe in plan_files:
            comp = getattr(fpe, "source_component", "")
            path = getattr(fpe, "path", "")
            if comp and path:
                comp_to_files.setdefault(comp, []).append(path)
        struct_files = getattr(structure_map, "files", None) or []
        for fe in struct_files:
            comp = getattr(fe, "source_component", "")
            path = getattr(fe, "path", "")
            if comp and path:
                if path not in comp_to_files.get(comp, []):
                    comp_to_files.setdefault(comp, []).append(path)

        for comp_name, file_paths in comp_to_files.items():
            comp_id = self._get_node_id(NODE_TYPE_COMPONENT, comp_name)
            if comp_id is None:
                continue
            for file_path in file_paths:
                file_id = self._get_node_id(NODE_TYPE_FILE, file_path)
                if file_id is None:
                    continue
                self._add_edge(
                    comp_id, file_id, EDGE_CONTAINS,
                    source=SOURCE_FILE_PLAN,
                    description=(
                        f"The {comp_name} component contains the "
                        f"{file_path} file."
                    ),
                )

    def _add_component_dependency_edges(
        self, registry: Any, dependency_report: Any,
    ) -> None:
        """Component → depends_on → Dependency edges."""
        deps = getattr(dependency_report, "dependencies", None) or []
        for dep in deps:
            dep_name = getattr(dep, "name", "")
            if not dep_name:
                continue
            dep_type = getattr(dep, "type", "library")
            node_type = (
                NODE_TYPE_LIBRARY if dep_type == "library"
                else NODE_TYPE_DEPENDENCY
            )
            dep_id = self._get_node_id(node_type, dep_name)
            if dep_id is None:
                continue
            source_components = getattr(dep, "source_components", None) or []
            for comp_name in source_components:
                comp_id = self._get_node_id(NODE_TYPE_COMPONENT, comp_name)
                if comp_id is None:
                    continue
                self._add_edge(
                    comp_id, dep_id, EDGE_DEPENDS_ON,
                    source=SOURCE_DEPENDENCY_REPORT,
                    description=(
                        f"The {comp_name} component depends on "
                        f"the {dep_name} {dep_type}."
                    ),
                )
                self._add_edge(
                    dep_id, comp_id, EDGE_REQUIRED_BY,
                    source=SOURCE_DEPENDENCY_REPORT,
                    description=(
                        f"The {dep_name} {dep_type} is required by "
                        f"the {comp_name} component."
                    ),
                )

    def _add_component_stage_edges(self, blueprint: Any) -> None:
        """Component → contained in → Stage edges (uses the EDGE_USES
        kind to represent "belongs to stage")."""
        plan = getattr(blueprint, "execution_plan", None)
        if plan is None:
            return
        phases = getattr(plan, "phases", None) or []
        for phase in phases:
            stage_name = getattr(phase, "name", "")
            stage_id = self._get_node_id(NODE_TYPE_STAGE, stage_name)
            if stage_id is None:
                continue
            components = getattr(phase, "components", None) or []
            for comp_name in components:
                comp_id = self._get_node_id(NODE_TYPE_COMPONENT, comp_name)
                if comp_id is None:
                    continue
                self._add_edge(
                    comp_id, stage_id, EDGE_USES,
                    source=SOURCE_BLUEPRINT,
                    description=(
                        f"The {comp_name} component is built in the "
                        f"{stage_name} stage."
                    ),
                )

    def _add_feature_stage_edges(self, blueprint: Any) -> None:
        """Feature → uses → Stage edges."""
        plan = getattr(blueprint, "execution_plan", None)
        if plan is None:
            return
        phases = getattr(plan, "phases", None) or []
        for phase in phases:
            stage_name = getattr(phase, "name", "")
            stage_id = self._get_node_id(NODE_TYPE_STAGE, stage_name)
            if stage_id is None:
                continue
            features = getattr(phase, "features", None) or []
            for feat_name in features:
                feat_id = self._get_node_id(NODE_TYPE_FEATURE, feat_name)
                if feat_id is None:
                    continue
                self._add_edge(
                    feat_id, stage_id, EDGE_USES,
                    source=SOURCE_BLUEPRINT,
                    description=(
                        f"The {feat_name} feature is built in the "
                        f"{stage_name} stage."
                    ),
                )

    def _add_stage_contains_edges(self, blueprint: Any) -> None:
        """Stage → contains → Component edges (the stage contains the
        components built in it)."""
        plan = getattr(blueprint, "execution_plan", None)
        if plan is None:
            return
        phases = getattr(plan, "phases", None) or []
        for phase in phases:
            stage_name = getattr(phase, "name", "")
            stage_id = self._get_node_id(NODE_TYPE_STAGE, stage_name)
            if stage_id is None:
                continue
            components = getattr(phase, "components", None) or []
            for comp_name in components:
                comp_id = self._get_node_id(NODE_TYPE_COMPONENT, comp_name)
                if comp_id is None:
                    continue
                self._add_edge(
                    stage_id, comp_id, EDGE_CONTAINS,
                    source=SOURCE_BLUEPRINT,
                    description=(
                        f"The {stage_name} stage contains the "
                        f"{comp_name} component."
                    ),
                )

    def _add_folder_file_edges(self, structure_map: Any) -> None:
        """Folder → contains → File edges."""
        struct_files = getattr(structure_map, "files", None) or []
        for fe in struct_files:
            file_path = getattr(fe, "path", "")
            folder = getattr(fe, "folder", "")
            if not file_path or not folder:
                continue
            file_id = self._get_node_id(NODE_TYPE_FILE, file_path)
            folder_id = self._get_node_id(NODE_TYPE_FOLDER, folder)
            if file_id is None or folder_id is None:
                continue
            self._add_edge(
                folder_id, file_id, EDGE_CONTAINS,
                source=SOURCE_STRUCTURE,
                description=(
                    f"The {folder} folder contains the {file_path} file."
                ),
            )

    def _add_file_dependency_edges(
        self, file_plan: Any, dependency_report: Any,
    ) -> None:
        """File → imports → Dependency edges.

        A file imports the dependencies that its component requires.
        """
        # Build a component → dependencies map.
        comp_to_deps: Dict[str, List[str]] = {}
        deps = getattr(dependency_report, "dependencies", None) or []
        for dep in deps:
            dep_name = getattr(dep, "name", "")
            source_components = getattr(dep, "source_components", None) or []
            for comp_name in source_components:
                comp_to_deps.setdefault(comp_name, []).append(dep_name)

        # Build a file → component map.
        file_to_comp: Dict[str, str] = {}
        plan_files = getattr(file_plan, "files", None) or []
        for fpe in plan_files:
            comp = getattr(fpe, "source_component", "")
            path = getattr(fpe, "path", "")
            if comp and path:
                file_to_comp[path] = comp

        for file_path, comp_name in file_to_comp.items():
            file_id = self._get_node_id(NODE_TYPE_FILE, file_path)
            if file_id is None:
                continue
            for dep_name in comp_to_deps.get(comp_name, []):
                dep_type = "library"
                for dep in deps:
                    if getattr(dep, "name", "") == dep_name:
                        dep_type = getattr(dep, "type", "library")
                        break
                node_type = (
                    NODE_TYPE_LIBRARY if dep_type == "library"
                    else NODE_TYPE_DEPENDENCY
                )
                dep_id = self._get_node_id(node_type, dep_name)
                if dep_id is None:
                    continue
                self._add_edge(
                    file_id, dep_id, EDGE_IMPORTS,
                    source=SOURCE_FILE_PLAN,
                    description=(
                        f"The {file_path} file imports the "
                        f"{dep_name} {dep_type}."
                    ),
                )

    def _add_dependency_dependency_edges(
        self, dependency_report: Any,
    ) -> None:
        """Dependency → depends_on → Dependency edges."""
        deps = getattr(dependency_report, "dependencies", None) or []
        # Build a map of dep name → type.
        dep_types: Dict[str, str] = {}
        for dep in deps:
            dep_types[getattr(dep, "name", "")] = getattr(
                dep, "type", "library",
            )
        for dep in deps:
            dep_name = getattr(dep, "name", "")
            dep_type = getattr(dep, "type", "library")
            node_type = (
                NODE_TYPE_LIBRARY if dep_type == "library"
                else NODE_TYPE_DEPENDENCY
            )
            dep_id = self._get_node_id(node_type, dep_name)
            if dep_id is None:
                continue
            depends_on = getattr(dep, "depends_on", None) or []
            for other_name in depends_on:
                other_type = dep_types.get(other_name, "library")
                other_node_type = (
                    NODE_TYPE_LIBRARY if other_type == "library"
                    else NODE_TYPE_DEPENDENCY
                )
                other_id = self._get_node_id(other_node_type, other_name)
                if other_id is None:
                    continue
                self._add_edge(
                    dep_id, other_id, EDGE_DEPENDS_ON,
                    source=SOURCE_DEPENDENCY_REPORT,
                    description=(
                        f"The {dep_name} {dep_type} depends on "
                        f"the {other_name} {other_type}."
                    ),
                )

    def _add_file_file_edges(self, file_plan: Any) -> None:
        """File → imports → File edges (from the file plan's file
        relationships)."""
        relationships = getattr(file_plan, "relationships", None) or []
        for rel in relationships:
            source = getattr(rel, "source", "")
            target = getattr(rel, "target", "")
            kind = getattr(rel, "kind", "imports")
            if not source or not target:
                continue
            source_id = self._get_node_id(NODE_TYPE_FILE, source)
            target_id = self._get_node_id(NODE_TYPE_FILE, target)
            if source_id is None or target_id is None:
                continue
            # Map the file-plan relationship kind to an edge kind.
            edge_kind = self._map_relationship_kind(kind)
            self._add_edge(
                source_id, target_id, edge_kind,
                source=SOURCE_FILE_PLAN,
                description=getattr(rel, "description", ""),
            )

    def _add_relationship_edges(
        self,
        blueprint: Any,
        registry: Any,
        structure_map: Any,
        file_plan: Any,
        dependency_report: Any,
        project_context: Any,
    ) -> None:
        """Add edges from the relationship lists in all artefacts.

        The relationships in the upstream artefacts are normalised to
        graph edges.  Each relationship has a source, a target, and a
        kind.  We attempt to resolve the source and target to existing
        node IDs (trying every node type in turn).
        """
        # Collect all relationships from all artefacts.
        all_relationships: List[Tuple[str, str, str, str, str]] = []
        # (source_name, target_name, kind, source_artefact, description)

        for rel in getattr(blueprint, "relationships", None) or []:
            all_relationships.append((
                getattr(rel, "source", ""),
                getattr(rel, "target", ""),
                getattr(rel, "kind", "depends_on"),
                SOURCE_BLUEPRINT,
                getattr(rel, "description", ""),
            ))
        for edge in getattr(registry, "relationships", None) or []:
            all_relationships.append((
                getattr(edge, "source", ""),
                getattr(edge, "target", ""),
                getattr(edge, "kind", "depends_on"),
                SOURCE_COMPONENT_REGISTRY,
                getattr(edge, "description", ""),
            ))
        for folder in getattr(structure_map, "folders", None) or []:
            for rel in getattr(folder, "relationships", None) or []:
                all_relationships.append((
                    getattr(rel, "source", ""),
                    getattr(rel, "target", ""),
                    getattr(rel, "kind", "depends_on"),
                    SOURCE_STRUCTURE,
                    getattr(rel, "description", ""),
                ))
        for fe in getattr(structure_map, "files", None) or []:
            for rel in getattr(fe, "relationships", None) or []:
                all_relationships.append((
                    getattr(rel, "source", ""),
                    getattr(rel, "target", ""),
                    getattr(rel, "kind", "depends_on"),
                    SOURCE_STRUCTURE,
                    getattr(rel, "description", ""),
                ))
        for rel in getattr(dependency_report, "relationships", None) or []:
            all_relationships.append((
                getattr(rel, "source", ""),
                getattr(rel, "target", ""),
                getattr(rel, "kind", "depends_on"),
                SOURCE_DEPENDENCY_REPORT,
                getattr(rel, "description", ""),
            ))

        for source_name, target_name, kind, source_art, desc in all_relationships:
            if not source_name or not target_name:
                continue
            source_id = self._resolve_node_id(source_name)
            target_id = self._resolve_node_id(target_name)
            if source_id is None or target_id is None:
                continue
            edge_kind = self._map_relationship_kind(kind)
            self._add_edge(
                source_id, target_id, edge_kind,
                source=source_art,
                description=desc,
            )

    def _add_project_context_edges(self, project_context: Any) -> None:
        """Add edges from the project context's relationships and links.

        The project context (Specification 010) already normalised the
        relationships and links.  We add them as graph edges.
        """
        if project_context is None:
            return

        # Relationships.
        relationships = getattr(project_context, "relationships", None) or []
        for rel in relationships:
            source_name = getattr(rel, "source", "")
            target_name = getattr(rel, "target", "")
            kind = getattr(rel, "kind", "depends_on")
            if not source_name or not target_name:
                continue
            source_id = self._resolve_node_id(source_name)
            target_id = self._resolve_node_id(target_name)
            if source_id is None or target_id is None:
                continue
            edge_kind = self._map_relationship_kind(kind)
            self._add_edge(
                source_id, target_id, edge_kind,
                source=SOURCE_PROJECT_CONTEXT,
                description=getattr(rel, "description", ""),
            )

        # Context links (the precomputed link indices from Spec 010).
        links = getattr(project_context, "links", None) or []
        for link in links:
            source_name = getattr(link, "source", "")
            target_name = getattr(link, "target", "")
            kind = getattr(link, "kind", "")
            if not source_name or not target_name:
                continue
            source_id = self._resolve_node_id(source_name)
            target_id = self._resolve_node_id(target_name)
            if source_id is None or target_id is None:
                continue
            edge_kind = self._map_link_kind(kind)
            self._add_edge(
                source_id, target_id, edge_kind,
                source=SOURCE_PROJECT_CONTEXT,
                description="",
            )

    # ------------------------------------------------------------------ #
    # Resolution helpers
    # ------------------------------------------------------------------ #

    def _resolve_node_id(self, name: str) -> Optional[str]:
        """Resolve an element name to a node ID.

        We try the node-by-name index first (the first registered node
        with that name).  When the name is a file path, we try the file
        node type.  When the name looks like a dependency, we try the
        library/dependency node types.
        """
        if not name:
            return None
        # Try an exact match by (type, name) for each known type.
        for node_type in ALL_NODE_TYPES_FOR_RESOLUTION:
            node_id = self._node_id_by_type_and_name.get((node_type, name))
            if node_id is not None:
                return node_id
        return None

    def _map_relationship_kind(self, kind: str) -> str:
        """Map an arbitrary relationship kind to an edge kind."""
        kind_lower = (kind or "").lower().replace("-", "_")
        mapping = {
            "depends_on": EDGE_DEPENDS_ON,
            "uses": EDGE_USES,
            "calls": EDGE_CALLS,
            "creates": EDGE_CREATES,
            "reads": EDGE_READS,
            "writes": EDGE_WRITES,
            "extends": EDGE_EXTENDS,
            "implements": EDGE_IMPLEMENTS,
            "contains": EDGE_CONTAINS,
            "references": EDGE_REFERENCES,
            "references": EDGE_REFERENCES,
            "imports": EDGE_IMPORTS,
            "import": EDGE_IMPORTS,
            "required_by": EDGE_REQUIRED_BY,
            "manages": EDGE_USES,
            "managed_by": EDGE_REQUIRED_BY,
            "stored_in": EDGE_USES,
            "configures": EDGE_REFERENCES,
            "documents": EDGE_REFERENCES,
            "tested_by": EDGE_USES,
            "requires": EDGE_DEPENDS_ON,
            "conflicts_with": EDGE_REFERENCES,
            "replaces": EDGE_REFERENCES,
        }
        return mapping.get(kind_lower, EDGE_REFERENCES)

    def _map_link_kind(self, kind: str) -> str:
        """Map a project-context link kind to an edge kind."""
        kind_lower = (kind or "").lower().replace("-", "_")
        mapping = {
            "feature_to_component": EDGE_IMPLEMENTS,
            "component_to_file": EDGE_CONTAINS,
            "file_to_dependency": EDGE_IMPORTS,
            "dependency_to_stage": EDGE_USES,
            "component_to_stage": EDGE_USES,
            "feature_to_stage": EDGE_USES,
        }
        return mapping.get(kind_lower, EDGE_REFERENCES)

    # ------------------------------------------------------------------ #
    # Provenance
    # ------------------------------------------------------------------ #

    def _build_provenance(
        self,
        blueprint: Any,
        validation_report: Any,
        structure_map: Any,
        registry: Any,
        file_plan: Any,
        dependency_report: Any,
        project_context: Any,
    ) -> GraphProvenance:
        identity = getattr(blueprint, "identity", None)
        project_name = getattr(identity, "name", "") if identity else ""
        return GraphProvenance(
            project_name=project_name,
            blueprint_name=project_name,
            validation_status=getattr(validation_report, "status", ""),
            structure_map_name=getattr(structure_map, "project_name", ""),
            component_registry_name=getattr(registry, "project_name", ""),
            file_plan_name=getattr(file_plan, "project_name", ""),
            dependency_report_name=getattr(
                dependency_report, "project_name", "",
            ),
            project_context_name=(
                getattr(
                    getattr(project_context, "goal", None),
                    "name", "",
                )
                if project_context is not None else ""
            ),
            all_sources_used=list(ALL_SOURCES),
        )


# The node types to try when resolving a name to a node ID, in order of
# priority.  Components, files, and dependencies are the most common
# relationship endpoints, so they are tried first.
ALL_NODE_TYPES_FOR_RESOLUTION = (
    NODE_TYPE_COMPONENT,
    NODE_TYPE_FILE,
    NODE_TYPE_DEPENDENCY,
    NODE_TYPE_LIBRARY,
    NODE_TYPE_FEATURE,
    NODE_TYPE_FOLDER,
    NODE_TYPE_STAGE,
    NODE_TYPE_SERVICE,
    NODE_TYPE_MIDDLEWARE,
    NODE_TYPE_REPOSITORY,
    NODE_TYPE_DATABASE_TABLE,
    NODE_TYPE_ROUTE,
    NODE_TYPE_COMMAND,
    NODE_TYPE_CONFIGURATION,
    NODE_TYPE_ENVIRONMENT_VARIABLE,
    NODE_TYPE_PROJECT,
)


__all__ = ["GraphBuilder"]
