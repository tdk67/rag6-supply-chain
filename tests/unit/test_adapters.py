"""Unit tests for NetworkX and ChromaDB adapter implementations."""

from ports.registry import AdapterRegistry
from ports.base import VectorChunk


def test_networkx_adapter_topological_queries():
    graph = AdapterRegistry.get_graph_store()
    stats = graph.get_stats()
    assert stats["total_nodes"] > 50
    assert stats["total_edges"] > 100

    # 1. Single source components (returns list of dicts)
    single_sources = graph.find_single_source_components()
    assert len(single_sources) >= 1
    assert "node_id" in single_sources[0]
    assert "sole_supplier_name" in single_sources[0]

    # 2. Taiwan dependent components (Benchmark Q1)
    taiwan_comps = graph.find_taiwan_dependent_components()
    assert len(taiwan_comps) >= 1
    assert any("MI300X" in c.get("node_id", "") or "TSMC" in c.get("disruption_reason", "") for c in taiwan_comps)

    # 3. Cooling loop failure impact (Benchmark Q6)
    cooling_impact = graph.find_cooling_failure_impact("SKU-PUMP-HALL1-B")
    assert "affected_loops" in cooling_impact
    assert "affected_racks" in cooling_impact

    # 4. Neighbors and node traversal
    node = graph.get_node("SKU-GPU-MI300X")
    assert node is not None
    neighbors = graph.get_neighbors("SKU-GPU-MI300X")
    assert len(neighbors) >= 1


def test_chromadb_adapter_lifecycle_and_stats():
    vs = AdapterRegistry.get_vector_store()
    
    # 1. Upsert test chunks
    test_chunk = VectorChunk(
        chunk_id="test_adapter_chunk_001",
        doc_id="test_adapter_doc",
        text="Test chunk text for vector store adapter verification.",
        metadata={"is_active": True, "source_file": "test_adapter.txt", "doc_id": "test_adapter_doc"},
    )
    inserted = vs.upsert_chunks("table_summaries", [test_chunk])
    assert inserted == 1

    # 2. Stats
    stats = vs.get_collection_stats()
    assert stats["table_summaries"] >= 1

    # 3. Deprecate by doc_id
    dep_count = vs.deprecate_by_doc_id("test_adapter_doc")
    assert dep_count >= 1

    # Verify deprecated chunk is not returned when querying active chunks
    res = vs.query("table_summaries", "Test chunk text", 5, where_filter={"is_active": True})
    assert all(r.chunk_id != "test_adapter_chunk_001" for r in res)
