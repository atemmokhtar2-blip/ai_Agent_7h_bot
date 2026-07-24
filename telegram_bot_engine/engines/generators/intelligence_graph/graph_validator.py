"""
Graph validator (Specification 011).

The :class:`GraphValidator` validates the
:class:`ProjectIntelligenceGraph` for internal consistency.  It
checks that:

* **No duplicate node IDs** — every node ID is unique.  The
  :class:`GraphBuilder` should already enforce this, but the
  validator double-checks.
* **No duplicate edge IDs** — every edge ID is unique.
* **No edges referencing non-existent nodes** — every edge's source
  and target node exists in the graph.  (This overlaps with the
  :class:`CircularDetector`'s broken-reference check, but the
  validator runs it independently for completeness.)
* **Every node type is a known type** — no node has a type that is
  not in the :data:`ALL_NODE_TYPES` set.
* **Every edge kind is a known kind** — no edge has a kind that is
  not in the :data:`ALL_EDGE_KINDS` set.
* **Every node has the required fields** — node_id, type, and name
  are non-empty strings.
* **No self-loops** — no edge has the same source and target node
  (a node pointing to itself is not a valid relationship).
* **The project node exists** — there is exactly one node of type
  ``project``.

The validator does **not** write code, create files, or make build
decisions.  It is a pure validation helper that produces
:class:`GraphFinding` objects.
"""

from __future__ import annotations

from typing import List, Set

from .graph_data import (
    ProjectIntelligenceGraph,
    GraphFinding,
    GraphNode,
    GraphEdge,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SEVERITY_INFO,
    CATEGORY_CONSISTENCY,
    ALL_NODE_TYPES,
    ALL_EDGE_KINDS,
    NODE_TYPE_PROJECT,
)


class GraphValidator:
    """Validate the intelligence graph for internal consistency.

    The validator is stateless — it takes the graph and returns a
    list of :class:`GraphFinding` objects.
    """

    def validate(
        self, graph: ProjectIntelligenceGraph,
    ) -> List[GraphFinding]:
        """Validate the graph and return a list of findings.

        Findings with ``severity == SEVERITY_ERROR`` indicate
        inconsistencies that make the graph unreliable for
        downstream engines.  Findings with
        ``severity == SEVERITY_WARNING`` indicate potential issues
        that downstream engines should be aware of.
        """
        findings: List[GraphFinding] = []

        findings.extend(self._check_duplicate_node_ids(graph))
        findings.extend(self._check_duplicate_edge_ids(graph))
        findings.extend(self._check_edges_reference_existing_nodes(graph))
        findings.extend(self._check_node_types(graph))
        findings.extend(self._check_edge_kinds(graph))
        findings.extend(self._check_node_required_fields(graph))
        findings.extend(self._check_self_loops(graph))
        findings.extend(self._check_project_node_exists(graph))
        findings.extend(self._check_indices_consistency(graph))

        return findings

    # ------------------------------------------------------------------ #
    # Duplicate node IDs
    # ------------------------------------------------------------------ #

    def _check_duplicate_node_ids(
        self, graph: ProjectIntelligenceGraph,
    ) -> List[GraphFinding]:
        """Check for duplicate node IDs in the raw node list."""
        findings: List[GraphFinding] = []
        seen: Set[str] = set()
        for node in graph.nodes:
            if node.node_id in seen:
                findings.append(GraphFinding(
                    severity=SEVERITY_ERROR,
                    code="duplicate_node_id",
                    message=(
                        f"Duplicate node ID '{node.node_id}'. "
                        f"Node IDs must be unique."
                    ),
                    affected=node.node_id,
                    category=CATEGORY_CONSISTENCY,
                    resolution_hint=(
                        "Ensure the graph builder deduplicates "
                        "nodes by (type, name)."
                    ),
                ))
            seen.add(node.node_id)
        return findings

    # ------------------------------------------------------------------ #
    # Duplicate edge IDs
    # ------------------------------------------------------------------ #

    def _check_duplicate_edge_ids(
        self, graph: ProjectIntelligenceGraph,
    ) -> List[GraphFinding]:
        """Check for duplicate edge IDs in the raw edge list."""
        findings: List[GraphFinding] = []
        seen: Set[str] = set()
        for edge in graph.edges:
            if edge.edge_id in seen:
                findings.append(GraphFinding(
                    severity=SEVERITY_ERROR,
                    code="duplicate_edge_id",
                    message=(
                        f"Duplicate edge ID '{edge.edge_id}'. "
                        f"Edge IDs must be unique."
                    ),
                    affected=edge.edge_id,
                    category=CATEGORY_CONSISTENCY,
                    resolution_hint=(
                        "Ensure the graph builder deduplicates "
                        "edges by (source_id, kind, target_id)."
                    ),
                ))
            seen.add(edge.edge_id)
        return findings

    # ------------------------------------------------------------------ #
    # Edges referencing non-existent nodes
    # ------------------------------------------------------------------ #

    def _check_edges_reference_existing_nodes(
        self, graph: ProjectIntelligenceGraph,
    ) -> List[GraphFinding]:
        """Check that every edge's source and target exist as nodes."""
        findings: List[GraphFinding] = []

        node_ids: Set[str] = {n.node_id for n in graph.nodes}

        for edge in graph.edges:
            if edge.source_id not in node_ids:
                findings.append(GraphFinding(
                    severity=SEVERITY_ERROR,
                    code="edge_source_not_found",
                    message=(
                        f"Edge '{edge.edge_id}' references source "
                        f"node '{edge.source_id}' which does not "
                        f"exist."
                    ),
                    affected=edge.edge_id,
                    category=CATEGORY_CONSISTENCY,
                    resolution_hint=(
                        "Create the missing source node or "
                        "remove the edge."
                    ),
                ))
            if edge.target_id not in node_ids:
                findings.append(GraphFinding(
                    severity=SEVERITY_ERROR,
                    code="edge_target_not_found",
                    message=(
                        f"Edge '{edge.edge_id}' references target "
                        f"node '{edge.target_id}' which does not "
                        f"exist."
                    ),
                    affected=edge.edge_id,
                    category=CATEGORY_CONSISTENCY,
                    resolution_hint=(
                        "Create the missing target node or "
                        "remove the edge."
                    ),
                ))
        return findings

    # ------------------------------------------------------------------ #
    # Node type validity
    # ------------------------------------------------------------------ #

    def _check_node_types(
        self, graph: ProjectIntelligenceGraph,
    ) -> List[GraphFinding]:
        """Check that every node has a known type."""
        findings: List[GraphFinding] = []
        valid_types: Set[str] = set(ALL_NODE_TYPES)
        for node in graph.nodes:
            if node.type not in valid_types:
                findings.append(GraphFinding(
                    severity=SEVERITY_ERROR,
                    code="unknown_node_type",
                    message=(
                        f"Node '{node.node_id}' has unknown type "
                        f"'{node.type}'. Valid types are: "
                        f"{', '.join(ALL_NODE_TYPES)}."
                    ),
                    affected=node.node_id,
                    category=CATEGORY_CONSISTENCY,
                    resolution_hint=(
                        "Use one of the defined node type "
                        "constants."
                    ),
                ))
        return findings

    # ------------------------------------------------------------------ #
    # Edge kind validity
    # ------------------------------------------------------------------ #

    def _check_edge_kinds(
        self, graph: ProjectIntelligenceGraph,
    ) -> List[GraphFinding]:
        """Check that every edge has a known kind."""
        findings: List[GraphFinding] = []
        valid_kinds: Set[str] = set(ALL_EDGE_KINDS)
        for edge in graph.edges:
            if edge.kind not in valid_kinds:
                findings.append(GraphFinding(
                    severity=SEVERITY_ERROR,
                    code="unknown_edge_kind",
                    message=(
                        f"Edge '{edge.edge_id}' has unknown kind "
                        f"'{edge.kind}'. Valid kinds are: "
                        f"{', '.join(ALL_EDGE_KINDS)}."
                    ),
                    affected=edge.edge_id,
                    category=CATEGORY_CONSISTENCY,
                    resolution_hint=(
                        "Use one of the defined edge kind "
                        "constants."
                    ),
                ))
        return findings

    # ------------------------------------------------------------------ #
    # Node required fields
    # ------------------------------------------------------------------ #

    def _check_node_required_fields(
        self, graph: ProjectIntelligenceGraph,
    ) -> List[GraphFinding]:
        """Check that every node has non-empty node_id, type, and
        name."""
        findings: List[GraphFinding] = []
        for node in graph.nodes:
            if not node.node_id:
                findings.append(GraphFinding(
                    severity=SEVERITY_ERROR,
                    code="empty_node_id",
                    message=(
                        "A node has an empty node_id. Node IDs "
                        "must be non-empty strings."
                    ),
                    affected=node.name or "<unnamed>",
                    category=CATEGORY_CONSISTENCY,
                    resolution_hint=(
                        "Ensure the graph builder assigns a "
                        "unique node ID to every node."
                    ),
                ))
            if not node.type:
                findings.append(GraphFinding(
                    severity=SEVERITY_ERROR,
                    code="empty_node_type",
                    message=(
                        f"Node '{node.node_id}' has an empty "
                        f"type. Node types must be non-empty."
                    ),
                    affected=node.node_id,
                    category=CATEGORY_CONSISTENCY,
                    resolution_hint=(
                        "Ensure the graph builder assigns a "
                        "valid type to every node."
                    ),
                ))
            if not node.name:
                findings.append(GraphFinding(
                    severity=SEVERITY_WARNING,
                    code="empty_node_name",
                    message=(
                        f"Node '{node.node_id}' has an empty "
                        f"name. Node names should be non-empty "
                        f"for readability."
                    ),
                    affected=node.node_id,
                    category=CATEGORY_CONSISTENCY,
                    resolution_hint=(
                        "Ensure the graph builder assigns a "
                        "meaningful name to every node."
                    ),
                ))
        return findings

    # ------------------------------------------------------------------ #
    # Self-loops
    # ------------------------------------------------------------------ #

    def _check_self_loops(
        self, graph: ProjectIntelligenceGraph,
    ) -> List[GraphFinding]:
        """Check for edges where the source and target are the same
        node."""
        findings: List[GraphFinding] = []
        for edge in graph.edges:
            if edge.source_id == edge.target_id:
                findings.append(GraphFinding(
                    severity=SEVERITY_WARNING,
                    code="self_loop",
                    message=(
                        f"Edge '{edge.edge_id}' is a self-loop: "
                        f"source and target are both "
                        f"'{edge.source_id}'."
                    ),
                    affected=edge.edge_id,
                    category=CATEGORY_CONSISTENCY,
                    resolution_hint=(
                        "Remove the self-loop edge or restructure "
                        "the relationship."
                    ),
                ))
        return findings

    # ------------------------------------------------------------------ #
    # Project node existence
    # ------------------------------------------------------------------ #

    def _check_project_node_exists(
        self, graph: ProjectIntelligenceGraph,
    ) -> List[GraphFinding]:
        """Check that there is exactly one node of type 'project'."""
        findings: List[GraphFinding] = []
        project_nodes = graph.indices.nodes_by_type.get(
            NODE_TYPE_PROJECT, [],
        )
        if len(project_nodes) == 0:
            findings.append(GraphFinding(
                severity=SEVERITY_WARNING,
                code="missing_project_node",
                message=(
                    "The graph has no node of type 'project'. "
                    "The project node is the root of the graph "
                    "and should always exist."
                ),
                affected="",
                category=CATEGORY_CONSISTENCY,
                resolution_hint=(
                    "Ensure the blueprint provides a project "
                    "name so the project node can be created."
                ),
            ))
        elif len(project_nodes) > 1:
            findings.append(GraphFinding(
                severity=SEVERITY_ERROR,
                code="multiple_project_nodes",
                message=(
                    f"The graph has {len(project_nodes)} nodes "
                    f"of type 'project'. There must be exactly "
                    f"one project node."
                ),
                affected=", ".join(project_nodes),
                category=CATEGORY_CONSISTENCY,
                resolution_hint=(
                    "Ensure the graph builder creates only one "
                    "project node."
                ),
            ))
        return findings

    # ------------------------------------------------------------------ #
    # Indices consistency
    # ------------------------------------------------------------------ #

    def _check_indices_consistency(
        self, graph: ProjectIntelligenceGraph,
    ) -> List[GraphFinding]:
        """Check that the indices are consistent with the raw node
        and edge lists.

        The navigator should have built the indices from the raw
        lists, so the counts should match.  This check catches bugs
        where the indices were built from a different or stale set
        of nodes/edges.
        """
        findings: List[GraphFinding] = []

        # node_by_id should have the same number of entries as the
        # raw node list.
        if len(graph.indices.node_by_id) != len(graph.nodes):
            findings.append(GraphFinding(
                severity=SEVERITY_ERROR,
                code="index_node_count_mismatch",
                message=(
                    f"The node_by_id index has "
                    f"{len(graph.indices.node_by_id)} entries "
                    f"but there are {len(graph.nodes)} nodes."
                ),
                affected="",
                category=CATEGORY_CONSISTENCY,
                resolution_hint=(
                    "Rebuild the indices with the GraphNavigator."
                ),
            ))

        # edges_by_kind total should match the edge list.
        total_indexed_edges = sum(
            len(v) for v in graph.indices.edges_by_kind.values()
        )
        if total_indexed_edges != len(graph.edges):
            findings.append(GraphFinding(
                severity=SEVERITY_ERROR,
                code="index_edge_count_mismatch",
                message=(
                    f"The edges_by_kind index has "
                    f"{total_indexed_edges} total edges but "
                    f"there are {len(graph.edges)} edges."
                ),
                affected="",
                category=CATEGORY_CONSISTENCY,
                resolution_hint=(
                    "Rebuild the indices with the GraphNavigator."
                ),
            ))

        return findings


__all__ = ["GraphValidator"]
