"""Tests for first-run dataset provisioning (serverless/ephemeral deployments)."""

from __future__ import annotations

import pytest


def test_bootstrap_util_imports_and_status_shape():
    """dataset_status() returns a well-formed dict and never raises on missing data."""
    from utils.data_bootstrap import dataset_status

    status = dataset_status()
    assert set(["sqlite_ok", "graph_ok", "vector_ok", "provisioned"]).issubset(status.keys())
    assert status["provisioned"] == (
        status["sqlite_ok"] and status["graph_ok"] and status["vector_ok"]
    )


def test_graph_adapter_handles_missing_file_without_raise(tmp_path):
    """NetworkXAdapter must boot with an empty graph when the graph file is absent."""
    import networkx as nx
    from ports.graph_store.networkx_adapter import NetworkXAdapter

    missing_path = tmp_path / "does_not_exist.json"
    adapter = NetworkXAdapter(graph_path=str(missing_path))

    assert isinstance(adapter.graph, (nx.MultiDiGraph, nx.Graph))
    assert adapter.graph.number_of_nodes() == 0
    assert adapter.get_stats() == {"total_nodes": 0, "total_edges": 0}


def test_graph_adapter_loads_generated_graph(tmp_path):
    """Once a node-link JSON exists, the adapter loads it (post-generation pickup)."""
    import json
    from ports.graph_store.networkx_adapter import NetworkXAdapter

    graph_file = tmp_path / "graph.json"
    node_link = {
        "directed": True,
        "multigraph": True,
        "nodes": [
            {"id": "Facility-DC1-Frankfurt", "label": "Facility"},
            {"id": "SKU-GPU-MI300X", "label": "Component"},
        ],
        "edges": [
            {
                "source": "Facility-DC1-Frankfurt",
                "target": "SKU-GPU-MI300X",
                "key": 0,
                "relation": "HOUSES",
            }
        ],
    }
    graph_file.write_text(json.dumps(node_link), encoding="utf-8")

    adapter = NetworkXAdapter(graph_path=str(graph_file))
    assert adapter.graph.number_of_nodes() == 2
    assert adapter.graph.number_of_edges() == 1
    assert adapter.get_stats()["total_nodes"] == 2