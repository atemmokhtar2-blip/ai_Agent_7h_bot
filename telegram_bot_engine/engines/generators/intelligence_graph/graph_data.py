"""
Intelligence Graph data model (Specification 011).

This module defines the :class:`ProjectIntelligenceGraph` — the complete,
authoritative, intelligent graph representation of the entire project.  It
is the **single** artefact produced by the
:class:`~telegram_bot_engine.engines.generators.intelligence_graph.IntelligenceGraphEngine`.

The Intelligence Graph is built by converting **seven** read-only artefacts
into a unified graph of nodes and edges:

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
   Resolution Engine),
7. the ``project_context`` (produced by the Project Context Engine,
   Specification 010).

The engine is **forbidden** from reading the user's request.

Design principles
-----------------
* **One intelligent graph.**  Every downstream engine reads the
  :class:`ProjectIntelligenceGraph` instead of re-reading the individual
  upstream artefacts.  The graph is the single, authoritative, navigable
  representation of the entire project.  Any downstream engine can reach
  any element in very few steps without re-analysing the project.
* **Traceability.**  Every node records the artefact it came from
  (``source``).  Every edge records the artefact the relationship was
  derived from (``source_artefact``).  Any decision taken by a downstream
  engine can trace its data back to the original source.
* **Navigation.**  The graph is built with precomputed O(1) look-up
  indices so that a downstream engine can start from any node (a feature,
  a component, a file, a dependency, a class, a function, a route, a
  command, a configuration, an environment variable, a service, a
  middleware, a repository, a database table) and reach any other node
  in constant time.
* **No build decisions.**  The Intelligence Graph provides **information**
  and **navigation**, not decisions.  It does not decide which file to
  generate first, which library to install first, or how to structure the
  code.  It only provides the graph so that decision-making engines can
  act.
* **Quality rules.**  Each node has a Unique ID, a Type, a Description,
  Relationships, a Priority, an Owner Engine, and a Source.
* **Circular detection.**  The graph detects circular dependencies, broken
  references, unused components, orphan files, and dead components.
* **Performance.**  The graph is built once and queried many times.
  Look-up indices (by ID, by type, by name) are precomputed so that
  downstream engines can access any information in constant time without
  re-analysing the project.  No graph rebuild is required if the project
  is unchanged.
* **Scalability.**  The graph is a plain data container that grows
  linearly with the number of elements.  No O(n²) operations are
  performed during construction or querying.  The graph works equally
  well for small, medium, large, and very large projects (millions of
  lines).

The graph is a plain data container — no logic lives here.  The engine
and its helpers populate it; downstream consumers read it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------#
# Source-artefact constants
# ---------------------------------------------------------------------------#
#
# Every node and edge inside the Intelligence Graph records the artefact it
# was derived from.  These constants are the stable identifiers for the
# seven upstream artefacts.

SOURCE_BLUEPRINT = "blueprint"
SOURCE_VALIDATION = "validation"
SOURCE_STRUCTURE = "structure"
SOURCE_COMPONENT_REGISTRY = "component_registry"
SOURCE_FILE_PLAN = "file_plan"
SOURCE_DEPENDENCY_REPORT = "dependency_report"
SOURCE_PROJECT_CONTEXT = "project_context"

ALL_SOURCES = (
    SOURCE_BLUEPRINT,
    SOURCE_VALIDATION,
    SOURCE_STRUCTURE,
    SOURCE_COMPONENT_REGISTRY,
    SOURCE_FILE_PLAN,
    SOURCE_DEPENDENCY_REPORT,
    SOURCE_PROJECT_CONTEXT,
)


# ---------------------------------------------------------------------------#
# Severity constants
# ---------------------------------------------------------------------------#

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

ALL_SEVERITIES = (SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO)


# ---------------------------------------------------------------------------#
# Node-type constants
# ---------------------------------------------------------------------------#
#
# The graph nodes are typed.  Every element in the project becomes a node
# of one of these types.

NODE_TYPE_PROJECT = "project"
NODE_TYPE_FOLDER = "folder"
NODE_TYPE_FILE = "file"
NODE_TYPE_CLASS = "class"
NODE_TYPE_FUNCTION = "function"
NODE_TYPE_INTERFACE = "interface"
NODE_TYPE_COMPONENT = "component"
NODE_TYPE_FEATURE = "feature"
NODE_TYPE_DEPENDENCY = "dependency"
NODE_TYPE_LIBRARY = "library"
NODE_TYPE_DATABASE_TABLE = "database_table"
NODE_TYPE_ROUTE = "route"
NODE_TYPE_COMMAND = "command"
NODE_TYPE_CONFIGURATION = "configuration"
NODE_TYPE_ENVIRONMENT_VARIABLE = "environment_variable"
NODE_TYPE_SERVICE = "service"
NODE_TYPE_MIDDLEWARE = "middleware"
NODE_TYPE_REPOSITORY = "repository"
NODE_TYPE_STAGE = "stage"

ALL_NODE_TYPES = (
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
)


# ---------------------------------------------------------------------------#
# Edge-kind (relationship) constants
# ---------------------------------------------------------------------------#
#
# The graph edges are typed.  Every relationship between two elements
# becomes an edge of one of these kinds.  These correspond to the
# relationship kinds required by the specification: Uses, Imports,
# Depends On, Calls, Creates, Reads, Writes, Extends, Implements,
# Contains, References, Required By.

EDGE_USES = "uses"
EDGE_IMPORTS = "imports"
EDGE_DEPENDS_ON = "depends_on"
EDGE_CALLS = "calls"
EDGE_CREATES = "creates"
EDGE_READS = "reads"
EDGE_WRITES = "writes"
EDGE_EXTENDS = "extends"
EDGE_IMPLEMENTS = "implements"
EDGE_CONTAINS = "contains"
EDGE_REFERENCES = "references"
EDGE_REQUIRED_BY = "required_by"

ALL_EDGE_KINDS = (
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


# ---------------------------------------------------------------------------#
# Detection category constants (for circular detection findings)
# ---------------------------------------------------------------------------#

CATEGORY_CIRCULAR_DEPENDENCY = "circular_dependency"
CATEGORY_BROKEN_REFERENCE = "broken_reference"
CATEGORY_UNUSED_COMPONENT = "unused_component"
CATEGORY_ORPHAN_FILE = "orphan_file"
CATEGORY_DEAD_COMPONENT = "dead_component"
CATEGORY_CONSISTENCY = "consistency"
CATEGORY_STRUCTURE = "structure"

ALL_CATEGORIES = (
    CATEGORY_CIRCULAR_DEPENDENCY,
    CATEGORY_BROKEN_REFERENCE,
    CATEGORY_UNUSED_COMPONENT,
    CATEGORY_ORPHAN_FILE,
    CATEGORY_DEAD_COMPONENT,
    CATEGORY_CONSISTENCY,
    CATEGORY_STRUCTURE,
)


# ---------------------------------------------------------------------------#
# Graph node
# ---------------------------------------------------------------------------#

@dataclass
class GraphNode:
    """A single node in the Intelligence Graph.

    Every element in the project (the project itself, a folder, a file,
    a class, a function, an interface, a component, a feature, a
    dependency, a library, a database table, a route, a command, a
    configuration, an environment variable, a service, a middleware, a
    repository, a stage) becomes a :class:`GraphNode`.

    Quality rules (per the specification):
    * **Unique ID** — every node has a globally-unique identifier.
    * **Type** — every node has a node type (one of the ``NODE_TYPE_*``
      constants).
    * **Description** — every node has a human-readable description.
    * **Relationships** — the node's relationships are recorded as edges
      in the graph (not duplicated on the node, but the node records the
      IDs of its neighbours for convenience).
    * **Priority** — every node has a priority (lower values are built
      first).
    * **Owner Engine** — the engine that owns this element (the engine
      that will produce or manage it).
    * **Source** — the artefact this node was derived from.

    Attributes:
        node_id: The globally-unique node identifier.  The format is
            ``"<type>:<name>"`` (e.g. ``"component:database"``).
        type: The node type (one of the ``NODE_TYPE_*`` constants).
        name: The element name (component name, file path, dependency
            name, etc.).
        display_name: The human-readable name.
        description: A human-readable description of what this node
            represents.
        priority: The node priority (lower values are built first).
        owner_engine: The engine that owns this element.
        source: The artefact this node was derived from (one of the
            ``SOURCE_*`` constants).
        metadata: Additional, type-specific metadata (e.g. the file
            type, the dependency version, the component importance).
        neighbours: The IDs of the nodes this node is directly connected
            to (for convenience; the authoritative relationships are
            the edges in the graph).
    """

    node_id: str = ""
    type: str = NODE_TYPE_COMPONENT
    name: str = ""
    display_name: str = ""
    description: str = ""
    priority: int = 100
    owner_engine: str = ""
    source: str = SOURCE_BLUEPRINT
    metadata: Dict[str, Any] = field(default_factory=dict)
    neighbours: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "type": self.type,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "priority": self.priority,
            "owner_engine": self.owner_engine,
            "source": self.source,
            "metadata": dict(self.metadata),
            "neighbours": list(self.neighbours),
        }


# ---------------------------------------------------------------------------#
# Graph edge
# ---------------------------------------------------------------------------#

@dataclass
class GraphEdge:
    """A single directed edge in the Intelligence Graph.

    Edges connect nodes across the different layers of the project.  For
    example, an edge of kind ``EDGE_CONTAINS`` connects a folder node to
    the file nodes it contains; an edge of kind ``EDGE_DEPENDS_ON``
    connects a component node to the dependency node it requires.

    Attributes:
        edge_id: The globally-unique edge identifier.  The format is
            ``"<source_id>--<kind>-->[target_id]"``.
        source_id: The source node ID.
        target_id: The target node ID.
        kind: The edge kind (one of the ``EDGE_*`` constants).
        source: The artefact the relationship was derived from (one of
            the ``SOURCE_*`` constants).
        description: A human-readable description of the relationship.
    """

    edge_id: str = ""
    source_id: str = ""
    target_id: str = ""
    kind: str = EDGE_DEPENDS_ON
    source: str = SOURCE_BLUEPRINT
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "kind": self.kind,
            "source": self.source,
            "description": self.description,
        }


# ---------------------------------------------------------------------------#
# Graph finding
# ---------------------------------------------------------------------------#

@dataclass
class GraphFinding:
    """A single finding produced during graph building, navigation, or
    circular detection.

    Attributes:
        severity: ``"error"``, ``"warning"``, or ``"info"``.
        code: A short, machine-readable code (e.g.
            ``"circular_dependency"``).
        message: A human-readable description.
        affected: The ID or name of the affected element.
        category: The finding category (one of the ``CATEGORY_*``
            constants or ``"consistency"``).
        resolution_hint: An optional suggestion on how to fix the issue.
        cycle: For circular-dependency findings, the list of node IDs
            that form the cycle (in order).
    """

    severity: str = SEVERITY_WARNING
    code: str = ""
    message: str = ""
    affected: str = ""
    category: str = CATEGORY_CONSISTENCY
    resolution_hint: str = ""
    cycle: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "affected": self.affected,
            "category": self.category,
            "resolution_hint": self.resolution_hint,
            "cycle": list(self.cycle),
        }


# ---------------------------------------------------------------------------#
# Graph indices (precomputed for O(1) look-ups)
# ---------------------------------------------------------------------------#

@dataclass
class GraphIndices:
    """Precomputed look-up indices for the Intelligence Graph.

    These indices are built by the
    :class:`GraphNavigator` so that downstream engines can traverse the
    graph in O(1) time without re-analysing the project.

    Attributes:
        node_by_id: Node ID → :class:`GraphNode`.
        nodes_by_type: Node type → list of node IDs.
        node_by_name: Element name → node ID (for type-unambiguous names;
            the first registered wins, so callers should prefer
            type-qualified look-ups when names collide across types).
        node_id_by_type_and_name: (type, name) → node ID.
        edges_by_source: Source node ID → list of edges.
        edges_by_target: Target node ID → list of edges.
        out_edges: Source node ID → list of target node IDs.
        in_edges: Target node ID → list of source node IDs.
        out_edges_by_kind: (source node ID, edge kind) → list of target
            node IDs.
        in_edges_by_kind: (target node ID, edge kind) → list of source
            node IDs.
        edges_by_kind: Edge kind → list of edges.
    """

    node_by_id: Dict[str, GraphNode] = field(default_factory=dict)
    nodes_by_type: Dict[str, List[str]] = field(default_factory=dict)
    node_by_name: Dict[str, str] = field(default_factory=dict)
    node_id_by_type_and_name: Dict[tuple, str] = field(default_factory=dict)
    edges_by_source: Dict[str, List[GraphEdge]] = field(default_factory=dict)
    edges_by_target: Dict[str, List[GraphEdge]] = field(default_factory=dict)
    out_edges: Dict[str, List[str]] = field(default_factory=dict)
    in_edges: Dict[str, List[str]] = field(default_factory=dict)
    out_edges_by_kind: Dict[tuple, List[str]] = field(default_factory=dict)
    in_edges_by_kind: Dict[tuple, List[str]] = field(default_factory=dict)
    edges_by_kind: Dict[str, List[GraphEdge]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_count": len(self.node_by_id),
            "nodes_by_type": {
                k: list(v) for k, v in self.nodes_by_type.items()
            },
            "node_by_name": dict(self.node_by_name),
            "edges_by_source": {
                k: [e.edge_id for e in v]
                for k, v in self.edges_by_source.items()
            },
            "edges_by_target": {
                k: [e.edge_id for e in v]
                for k, v in self.edges_by_target.items()
            },
            "edges_by_kind": {
                k: [e.edge_id for e in v]
                for k, v in self.edges_by_kind.items()
            },
        }


# ---------------------------------------------------------------------------#
# Source provenance
# ---------------------------------------------------------------------------#

@dataclass
class GraphProvenance:
    """Records which upstream artefacts were used to build the graph.

    This is the traceability record required by the specification: any
    decision taken by a downstream engine can trace its data back to the
    original source artefact.

    Attributes:
        project_name: The name of the project (from the blueprint).
        blueprint_name: The name of the blueprint used.
        validation_status: The approval status of the blueprint.
        structure_map_name: The name of the structure map used.
        component_registry_name: The name of the component registry
            used.
        file_plan_name: The name of the file generation plan used.
        dependency_report_name: The name of the dependency resolution
            report used.
        project_context_name: The name recorded in the project context
            artefact.
        all_sources_used: The list of all source artefact identifiers
            that contributed to the graph.
    """

    project_name: str = ""
    blueprint_name: str = ""
    validation_status: str = ""
    structure_map_name: str = ""
    component_registry_name: str = ""
    file_plan_name: str = ""
    dependency_report_name: str = ""
    project_context_name: str = ""
    all_sources_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "blueprint_name": self.blueprint_name,
            "validation_status": self.validation_status,
            "structure_map_name": self.structure_map_name,
            "component_registry_name": self.component_registry_name,
            "file_plan_name": self.file_plan_name,
            "dependency_report_name": self.dependency_report_name,
            "project_context_name": self.project_context_name,
            "all_sources_used": list(self.all_sources_used),
        }


# ---------------------------------------------------------------------------#
# The full Project Intelligence Graph
# ---------------------------------------------------------------------------#

@dataclass
class ProjectIntelligenceGraph:
    """The complete, authoritative, intelligent graph of the project.

    This is the **only** object the Intelligence Graph Engine produces.
    It is stored in the generation context as the ``intelligence_graph``
    artefact.

    The graph is **read-only** for all downstream engines — no engine may
    modify it directly.  Any modification requires a dedicated engine.

    The graph is the **single reference point** for all downstream
    engines.  Instead of re-reading the seven upstream artefacts, every
    downstream engine reads the graph and uses the precomputed indices to
    access any piece of information in O(1) time and reach any element in
    very few steps.

    Attributes:
        nodes: The list of :class:`GraphNode` objects.
        edges: The list of :class:`GraphEdge` objects.
        indices: The :class:`GraphIndices` — precomputed O(1) look-up
            tables.
        findings: The list of :class:`GraphFinding` objects produced
            during graph building, navigation, and circular detection.
        provenance: The :class:`GraphProvenance` — traceability record.
        summary: A human-readable summary.
        notes: General notes about the graph.
        warnings: Warnings produced during graph building.
    """

    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    indices: GraphIndices = field(default_factory=GraphIndices)
    findings: List[GraphFinding] = field(default_factory=list)
    provenance: GraphProvenance = field(default_factory=GraphProvenance)
    summary: str = ""
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # -- convenience -------------------------------------------------------#

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def is_empty(self) -> bool:
        return self.node_count == 0

    @property
    def has_errors(self) -> bool:
        return any(f.severity == SEVERITY_ERROR for f in self.findings)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SEVERITY_ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SEVERITY_WARNING)

    @property
    def node_type_count(self) -> int:
        return len(self.indices.nodes_by_type)

    @property
    def edge_kind_count(self) -> int:
        return len(self.indices.edges_by_kind)

    # -- O(1) look-up helpers ---------------------------------------------#

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Return the node with the given ID (O(1))."""
        return self.indices.node_by_id.get(node_id)

    def get_node_by_name(self, name: str) -> Optional[GraphNode]:
        """Return the node with the given element name (O(1)).

        When multiple node types share the same name, the first
        registered node wins.  Prefer :meth:`get_node_by_type_and_name`
        when the type is known.
        """
        node_id = self.indices.node_by_name.get(name)
        if node_id is None:
            return None
        return self.indices.node_by_id.get(node_id)

    def get_node_by_type_and_name(
        self, node_type: str, name: str,
    ) -> Optional[GraphNode]:
        """Return the node with the given type and name (O(1))."""
        node_id = self.indices.node_id_by_type_and_name.get(
            (node_type, name),
        )
        if node_id is None:
            return None
        return self.indices.node_by_id.get(node_id)

    def nodes_of_type(self, node_type: str) -> List[GraphNode]:
        """Return all nodes of the given type (O(1) for the ID list)."""
        node_ids = self.indices.nodes_by_type.get(node_type, [])
        return [
            self.indices.node_by_id[nid]
            for nid in node_ids
            if nid in self.indices.node_by_id
        ]

    def node_ids_of_type(self, node_type: str) -> List[str]:
        """Return the IDs of all nodes of the given type (O(1))."""
        return list(self.indices.nodes_by_type.get(node_type, []))

    def outgoing(self, node_id: str) -> List[str]:
        """Return the IDs of nodes this node points to (O(1))."""
        return list(self.indices.out_edges.get(node_id, []))

    def incoming(self, node_id: str) -> List[str]:
        """Return the IDs of nodes that point to this node (O(1))."""
        return list(self.indices.in_edges.get(node_id, []))

    def outgoing_by_kind(
        self, node_id: str, kind: str,
    ) -> List[str]:
        """Return the IDs of nodes this node points to via the given
        edge kind (O(1))."""
        return list(
            self.indices.out_edges_by_kind.get((node_id, kind), [])
        )

    def incoming_by_kind(
        self, node_id: str, kind: str,
    ) -> List[str]:
        """Return the IDs of nodes that point to this node via the given
        edge kind (O(1))."""
        return list(
            self.indices.in_edges_by_kind.get((node_id, kind), [])
        )

    def edges_from(self, node_id: str) -> List[GraphEdge]:
        """Return all edges whose source is the given node (O(1))."""
        return list(self.indices.edges_by_source.get(node_id, []))

    def edges_to(self, node_id: str) -> List[GraphEdge]:
        """Return all edges whose target is the given node (O(1))."""
        return list(self.indices.edges_by_target.get(node_id, []))

    def edges_of_kind(self, kind: str) -> List[GraphEdge]:
        """Return all edges of the given kind (O(1))."""
        return list(self.indices.edges_by_kind.get(kind, []))

    # -- multi-hop navigation ---------------------------------------------#

    def neighbours(self, node_id: str) -> List[str]:
        """Return the IDs of all nodes directly connected to this node
        (either direction) (O(1))."""
        result: List[str] = []
        seen: set = set()
        for nid in self.indices.out_edges.get(node_id, []):
            if nid not in seen:
                seen.add(nid)
                result.append(nid)
        for nid in self.indices.in_edges.get(node_id, []):
            if nid not in seen:
                seen.add(nid)
                result.append(nid)
        return result

    def reachable(
        self,
        node_id: str,
        max_hops: int = 8,
    ) -> List[str]:
        """Return the IDs of all nodes reachable from the given node
        within ``max_hops`` steps (breadth-first).

        This is the navigation primitive required by the specification:
        any downstream engine can reach any element in very few steps
        without re-analysis.
        """
        if node_id not in self.indices.node_by_id:
            return []
        visited: List[str] = [node_id]
        seen: set = {node_id}
        frontier: List[str] = [node_id]
        for _ in range(max_hops):
            next_frontier: List[str] = []
            for nid in frontier:
                for target in self.indices.out_edges.get(nid, []):
                    if target not in seen:
                        seen.add(target)
                        visited.append(target)
                        next_frontier.append(target)
            if not next_frontier:
                break
            frontier = next_frontier
        return visited

    def shortest_path(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 16,
    ) -> List[str]:
        """Return the shortest path (list of node IDs) from the source
        to the target, or an empty list if no path exists within
        ``max_hops`` (breadth-first)."""
        if source_id not in self.indices.node_by_id:
            return []
        if target_id not in self.indices.node_by_id:
            return []
        if source_id == target_id:
            return [source_id]
        # Breadth-first search.
        from collections import deque
        queue: deque = deque([(source_id, [source_id])])
        seen: set = {source_id}
        while queue:
            nid, path = queue.popleft()
            if len(path) - 1 >= max_hops:
                continue
            for target in self.indices.out_edges.get(nid, []):
                if target == target_id:
                    return path + [target]
                if target not in seen:
                    seen.add(target)
                    queue.append((target, path + [target]))
        return []

    # -- finding management -----------------------------------------------#

    def add_finding(
        self,
        severity: str,
        code: str,
        message: str,
        affected: str = "",
        category: str = CATEGORY_CONSISTENCY,
        resolution_hint: str = "",
        cycle: Optional[List[str]] = None,
    ) -> None:
        """Add a finding to the graph."""
        self.findings.append(GraphFinding(
            severity=severity,
            code=code,
            message=message,
            affected=affected,
            category=category,
            resolution_hint=resolution_hint,
            cycle=list(cycle) if cycle else [],
        ))
        if severity == SEVERITY_WARNING:
            self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "finding_count": self.finding_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "node_type_count": self.node_type_count,
            "edge_kind_count": self.edge_kind_count,
            "summary": self.summary,
            "notes": list(self.notes),
            "warnings": list(self.warnings),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "indices": self.indices.to_dict(),
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
    # Data model
    "GraphNode",
    "GraphEdge",
    "GraphFinding",
    "GraphIndices",
    "GraphProvenance",
    "ProjectIntelligenceGraph",
]
