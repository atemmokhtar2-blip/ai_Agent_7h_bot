"""
Graph navigator (Specification 011).

The :class:`GraphNavigator` builds the precomputed O(1) look-up
indices that the :class:`ProjectIntelligenceGraph` uses to traverse
the entire graph in constant time.

The navigator is the navigation engine required by the specification:
it takes the raw list of nodes and edges produced by the
:class:`GraphBuilder` and builds a :class:`GraphIndices` object with
eleven precomputed dictionaries so that any downstream engine can:

* look up a node by ID, by type, by name, or by (type, name) pair in
  O(1) time,
* look up all edges whose source or target is a given node in O(1)
  time,
* look up all outgoing or incoming node IDs for a given node in O(1)
  time,
* look up all outgoing or incoming node IDs for a given node and a
  given edge kind in O(1) time,
* look up all edges of a given kind in O(1) time.

These indices are the foundation of the navigation primitive required
by the specification: any downstream engine can reach any element in
very few steps without re-analysing the project.

The navigator does **not** write code, create files, or make build
decisions.  It is a pure index-building helper.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .graph_data import (
    ProjectIntelligenceGraph,
    GraphIndices,
    GraphNode,
    GraphEdge,
    ALL_NODE_TYPES,
)


class GraphNavigator:
    """Build the O(1) look-up indices for the intelligence graph.

    The navigator is stateless — it takes the graph (whose nodes and
    edges were already populated by the :class:`GraphBuilder`) and
    builds the :class:`GraphIndices`, setting it on the graph.
    """

    def navigate(self, graph: ProjectIntelligenceGraph) -> ProjectIntelligenceGraph:
        """Build the indices on the graph and return the graph.

        This method mutates the graph in place (it sets the
        ``indices`` field) and also returns the graph for
        convenience.
        """
        indices = self._build_indices(graph.nodes, graph.edges)
        graph.indices = indices
        return graph

    # ------------------------------------------------------------------ #
    # Index building
    # ------------------------------------------------------------------ #

    def _build_indices(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
    ) -> GraphIndices:
        """Build all eleven O(1) look-up dictionaries from the raw
        node and edge lists.

        This is the core method that turns a flat list of nodes and
        edges into a navigable, O(1) graph structure.  After this
        method returns, every look-up the graph exposes is a simple
        dictionary access — no iteration, no scanning, no
        re-analysis.
        """
        indices = GraphIndices()

        # -- 1. node_by_id: node ID -> GraphNode ------------------------- #
        for node in nodes:
            indices.node_by_id[node.node_id] = node

        # -- 2. nodes_by_type: node type -> list of node IDs -------------- #
        # Pre-initialise all known node types so that the dictionary
        # has a key for every type (even if it has zero nodes), which
        # makes downstream look-ups simpler.
        for nt in ALL_NODE_TYPES:
            indices.nodes_by_type[nt] = []
        for node in nodes:
            indices.nodes_by_type.setdefault(node.type, []).append(
                node.node_id,
            )

        # -- 3. node_by_name: element name -> node ID ------------------- #
        # When multiple node types share the same name, the first
        # registered node wins.  Callers should prefer
        # node_id_by_type_and_name when the type is known.
        for node in nodes:
            if node.name not in indices.node_by_name:
                indices.node_by_name[node.name] = node.node_id

        # -- 4. node_id_by_type_and_name: (type, name) -> node ID -------- #
        for node in nodes:
            indices.node_id_by_type_and_name[(node.type, node.name)] = (
                node.node_id
            )

        # -- 5. edges_by_source: source node ID -> list of edges -------- #
        for edge in edges:
            indices.edges_by_source.setdefault(
                edge.source_id, [],
            ).append(edge)

        # -- 6. edges_by_target: target node ID -> list of edges -------- #
        for edge in edges:
            indices.edges_by_target.setdefault(
                edge.target_id, [],
            ).append(edge)

        # -- 7. out_edges: source node ID -> list of target node IDs ----- #
        for edge in edges:
            indices.out_edges.setdefault(
                edge.source_id, [],
            ).append(edge.target_id)

        # -- 8. in_edges: target node ID -> list of source node IDs ------ #
        for edge in edges:
            indices.in_edges.setdefault(
                edge.target_id, [],
            ).append(edge.source_id)

        # -- 9. out_edges_by_kind:
        #       (source node ID, edge kind) -> list of target node IDs -- #
        for edge in edges:
            key = (edge.source_id, edge.kind)
            indices.out_edges_by_kind.setdefault(key, []).append(
                edge.target_id,
            )

        # -- 10. in_edges_by_kind:
        #        (target node ID, edge kind) -> list of source node IDs - #
        for edge in edges:
            key = (edge.target_id, edge.kind)
            indices.in_edges_by_kind.setdefault(key, []).append(
                edge.source_id,
            )

        # -- 11. edges_by_kind: edge kind -> list of edges -------------- #
        for edge in edges:
            indices.edges_by_kind.setdefault(edge.kind, []).append(edge)

        return indices


__all__ = ["GraphNavigator"]
