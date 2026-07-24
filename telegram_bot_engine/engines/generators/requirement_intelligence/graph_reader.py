"""
Graph reader — reads the project intelligence graph from the generation
context.

The :class:`GraphReader` is responsible for obtaining the
``intelligence_graph`` artefact (produced by the
:class:`~telegram_bot_engine.engines.generators.intelligence_graph.IntelligenceGraphEngine`)
and returning a normalised :class:`GraphData` object.

The reader is tolerant: it never raises when the intelligence graph is
not available.  It returns a :class:`GraphData` with
``available=False`` in that case.

This module is a pure reader: it has no side effects and does not
modify the generation context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ....core.context import GenerationContext
from .report_data import SOURCE_INTELLIGENCE_GRAPH


# ---------------------------------------------------------------------------#
# Graph data
# ---------------------------------------------------------------------------#

@dataclass
class GraphData:
    """Normalised view of the project intelligence graph.

    This is a lightweight container that holds the information the
    Requirement Intelligence Engine needs from the Intelligence Graph.

    Attributes:
        node_count: The total number of nodes in the graph.
        edge_count: The total number of edges in the graph.
        node_types: The list of node types present in the graph.
        node_names: The list of node names (or ids).
        component_nodes: The list of component node names.
        feature_nodes: The list of feature node names.
        file_nodes: The list of file node names.
        dependency_nodes: The list of dependency node names.
        command_nodes: The list of command node names.
        database_table_nodes: The list of database-table node
            names.
        finding_count: The number of findings recorded in the
            graph.
        error_finding_count: The number of error-level findings.
        warning_finding_count: The number of warning-level
            findings.
        available: Whether the intelligence graph was available.
    """

    node_count: int = 0
    edge_count: int = 0
    node_types: List[str] = field(default_factory=list)
    node_names: List[str] = field(default_factory=list)
    component_nodes: List[str] = field(default_factory=list)
    feature_nodes: List[str] = field(default_factory=list)
    file_nodes: List[str] = field(default_factory=list)
    dependency_nodes: List[str] = field(default_factory=list)
    command_nodes: List[str] = field(default_factory=list)
    database_table_nodes: List[str] = field(default_factory=list)
    finding_count: int = 0
    error_finding_count: int = 0
    warning_finding_count: int = 0
    available: bool = False

    @property
    def source_artefact(self) -> str:
        return SOURCE_INTELLIGENCE_GRAPH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "node_types": list(self.node_types),
            "node_names": list(self.node_names),
            "component_nodes": list(self.component_nodes),
            "feature_nodes": list(self.feature_nodes),
            "file_nodes": list(self.file_nodes),
            "dependency_nodes": list(self.dependency_nodes),
            "command_nodes": list(self.command_nodes),
            "database_table_nodes": list(self.database_table_nodes),
            "finding_count": self.finding_count,
            "error_finding_count": self.error_finding_count,
            "warning_finding_count": self.warning_finding_count,
            "available": self.available,
        }


class GraphReader:
    """Reads the project intelligence graph from the generation
    context.

    The reader looks for the ``intelligence_graph`` artefact.  When
    present, it extracts the node count, edge count, node types, and
    the nodes grouped by type.  When absent, it returns a
    :class:`GraphData` with ``available=False``.
    """

    def read(self, context: GenerationContext) -> GraphData:
        """Read the intelligence graph and return a
        :class:`GraphData`."""
        graph = context.get("intelligence_graph")
        if graph is None:
            return GraphData(available=False)

        return self._read_from_graph(graph)

    # ----------------------------------------------------------------- #
    # Internal helpers
    # ----------------------------------------------------------------- #

    def _read_from_graph(self, graph: Any) -> GraphData:
        """Extract graph data from the intelligence graph artefact."""
        def get_attr(name: str, default: Any = None) -> Any:
            if hasattr(graph, name):
                return getattr(graph, name)
            if isinstance(graph, dict):
                return graph.get(name, default)
            return default

        nodes = get_attr("nodes", []) or []
        edges = get_attr("edges", []) or []
        node_count = self._count(nodes)
        edge_count = self._count(edges)

        node_types: List[str] = []
        node_names: List[str] = []
        component_nodes: List[str] = []
        feature_nodes: List[str] = []
        file_nodes: List[str] = []
        dependency_nodes: List[str] = []
        command_nodes: List[str] = []
        database_table_nodes: List[str] = []

        if isinstance(nodes, (list, tuple)):
            for node in nodes:
                node_type = self._get_field(node, "type")
                node_name = self._get_field(node, "name") or self._get_field(node, "id")
                if node_type:
                    node_types.append(node_type)
                if node_name:
                    node_names.append(node_name)
                if node_type == "component":
                    component_nodes.append(node_name)
                elif node_type == "feature":
                    feature_nodes.append(node_name)
                elif node_type == "file":
                    file_nodes.append(node_name)
                elif node_type == "dependency":
                    dependency_nodes.append(node_name)
                elif node_type == "command":
                    command_nodes.append(node_name)
                elif node_type == "database_table":
                    database_table_nodes.append(node_name)

        # Deduplicate node types while preserving order.
        seen = set()
        unique_types: List[str] = []
        for nt in node_types:
            if nt not in seen:
                seen.add(nt)
                unique_types.append(nt)

        # Findings
        findings = get_attr("findings", []) or []
        finding_count = self._count(findings)
        error_finding_count = 0
        warning_finding_count = 0
        if isinstance(findings, (list, tuple)):
            for finding in findings:
                severity = self._get_field(finding, "severity")
                if severity == "error":
                    error_finding_count += 1
                elif severity == "warning":
                    warning_finding_count += 1

        return GraphData(
            node_count=node_count,
            edge_count=edge_count,
            node_types=unique_types,
            node_names=node_names,
            component_nodes=component_nodes,
            feature_nodes=feature_nodes,
            file_nodes=file_nodes,
            dependency_nodes=dependency_nodes,
            command_nodes=command_nodes,
            database_table_nodes=database_table_nodes,
            finding_count=finding_count,
            error_finding_count=error_finding_count,
            warning_finding_count=warning_finding_count,
            available=True,
        )

    @staticmethod
    def _count(items: Any) -> int:
        if isinstance(items, (list, tuple)):
            return len(items)
        return 0

    @staticmethod
    def _get_field(item: Any, attr: str) -> str:
        if item is None:
            return ""
        if isinstance(item, dict):
            value = item.get(attr, "")
        elif hasattr(item, attr):
            value = getattr(item, attr, "")
        else:
            value = ""
        return str(value) if value is not None else ""


__all__ = ["GraphReader", "GraphData"]
