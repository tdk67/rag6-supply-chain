"""NetworkX implementation of the GraphStorePort interface."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional
import networkx as nx

from ports.base import GraphStorePort
from utils.config import resolve_path, load_config


class NetworkXAdapter(GraphStorePort):
    """Adapter for in-memory NetworkX knowledge graph operations."""

    def __init__(self, graph_path: Optional[str | Path] = None):
        if graph_path is not None:
            self.graph_file = resolve_path(graph_path)
        else:
            cfg = load_config()
            self.graph_file = resolve_path(cfg["paths"]["graph_file"])

        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self.load_graph()

    def load_graph(self):
        """Load knowledge graph preferring secure JSON format over binary pickle."""
        json_file = self.graph_file if self.graph_file.suffix == ".json" else self.graph_file.with_suffix(".json")
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "nodes" in data and ("links" in data or "edges" in data):
                    self.graph = nx.node_link_graph(data, multigraph=True, directed=True)
                    return
            except Exception:
                pass

        if self.graph_file.exists():
            with open(self.graph_file, "rb") as f:
                self.graph = pickle.load(f)
        else:
            self.graph = nx.MultiDiGraph()

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        if node_id in self.graph:
            data = dict(self.graph.nodes[node_id])
            data["node_id"] = node_id
            return data
        return None

    def find_nodes(self, label: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        matches = []
        for n, data in self.graph.nodes(data=True):
            if data.get("label") == label:
                if filters:
                    if all(data.get(k) == v for k, v in filters.items()):
                        item = dict(data)
                        item["node_id"] = n
                        matches.append(item)
                else:
                    item = dict(data)
                    item["node_id"] = n
                    matches.append(item)
        return matches

    def get_neighbors(
        self, node_id: str, direction: str = "both", relation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if node_id not in self.graph:
            return []

        neighbors = []
        # Successors (outgoing)
        if direction in ("out", "both"):
            for succ in self.graph.successors(node_id):
                edge_dict = self.graph.get_edge_data(node_id, succ)
                for key, edge_data in edge_dict.items():
                    if relation is None or edge_data.get("relation") == relation:
                        node_data = dict(self.graph.nodes[succ])
                        node_data["node_id"] = succ
                        node_data["relation"] = edge_data.get("relation")
                        node_data["direction"] = "outgoing"
                        neighbors.append(node_data)

        # Predecessors (incoming)
        if direction in ("in", "both"):
            for pred in self.graph.predecessors(node_id):
                edge_dict = self.graph.get_edge_data(pred, node_id)
                for key, edge_data in edge_dict.items():
                    if relation is None or edge_data.get("relation") == relation:
                        node_data = dict(self.graph.nodes[pred])
                        node_data["node_id"] = pred
                        node_data["relation"] = edge_data.get("relation")
                        node_data["direction"] = "incoming"
                        neighbors.append(node_data)

        return neighbors

    def execute_traversal(self, start_label: str, relations: List[str], target_label: str) -> List[Dict[str, Any]]:
        """Find paths conforming to multi-hop relation sequence."""
        results = []
        start_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("label") == start_label]
        for s in start_nodes:
            current_level = [s]
            for rel in relations:
                next_level = []
                for curr in current_level:
                    for succ in self.graph.successors(curr):
                        edges = self.graph.get_edge_data(curr, succ)
                        for k, ed in edges.items():
                            if ed.get("relation") == rel:
                                next_level.append(succ)
                current_level = next_level
                if not current_level:
                    break

            for target in current_level:
                if self.graph.nodes[target].get("label") == target_label:
                    results.append({
                        "start_node": s,
                        "target_node": target,
                        "target_data": dict(self.graph.nodes[target]),
                    })
        return results

    def find_single_source_components(self) -> List[Dict[str, Any]]:
        """Identify components that have exactly one qualified supplier (Benchmark Q3)."""
        single_sources = []
        for n, d in self.graph.nodes(data=True):
            if d.get("label") == "Component":
                suppliers = []
                for succ in self.graph.successors(n):
                    edges = self.graph.get_edge_data(n, succ)
                    for k, ed in edges.items():
                        if ed.get("relation") == "SUPPLIED_BY":
                            suppliers.append(succ)
                if len(suppliers) == 1:
                    sup_data = self.graph.nodes[suppliers[0]]
                    comp_info = dict(d)
                    comp_info["node_id"] = n
                    comp_info["sole_supplier_id"] = suppliers[0]
                    comp_info["sole_supplier_name"] = sup_data.get("name", suppliers[0])
                    single_sources.append(comp_info)
        return single_sources

    def find_taiwan_dependent_components(self) -> List[Dict[str, Any]]:
        """Traverse graph to find components fabricated or sub-contracted in Taiwan (Benchmark Q1)."""
        affected = []
        taiwan_node = "Country-Taiwan"
        for n, d in self.graph.nodes(data=True):
            if d.get("label") == "Component":
                is_affected = False
                reason = ""
                # Check direct fabrication
                if self.graph.has_edge(n, taiwan_node):
                    is_affected = True
                    reason = "Direct wafer/assembly fabrication in Taiwan"
                else:
                    # Check upstream supplier/subtier location
                    for succ in self.graph.successors(n):
                        if self.graph.has_edge(succ, taiwan_node):
                            is_affected = True
                            reason = f"Upstream partner {succ} located in Taiwan"
                            break

                if is_affected:
                    comp_data = dict(d)
                    comp_data["node_id"] = n
                    comp_data["disruption_reason"] = reason
                    affected.append(comp_data)
        return affected

    def find_cooling_failure_impact(self, pump_sku: str = "SKU-PUMP-HALL1-B") -> Dict[str, Any]:
        """Find cooling loops, server racks, and heat export impact from pump failure (Benchmark Q6)."""
        affected_loops = []
        for loop, succ in self.graph.edges():
            edges = self.graph.get_edge_data(loop, succ)
            for k, ed in edges.items():
                if succ == pump_sku and ed.get("relation") == "DEPENDS_ON_PUMP":
                    affected_loops.append(loop)

        affected_racks = []
        for loop in affected_loops:
            for pred in self.graph.predecessors(loop):
                edges = self.graph.get_edge_data(pred, loop)
                for k, ed in edges.items():
                    if ed.get("relation") == "COOLED_BY" and self.graph.nodes[pred].get("label") == "Rack":
                        rack_info = dict(self.graph.nodes[pred])
                        rack_info["rack_id"] = pred
                        affected_racks.append(rack_info)

        return {
            "pump_sku": pump_sku,
            "affected_loops": affected_loops,
            "affected_racks": affected_racks,
            "total_racks_affected": len(affected_racks),
            "district_heating_impact": True if "Loop-A" in affected_loops else False,
        }

    def get_stats(self) -> Dict[str, int]:
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
        }
