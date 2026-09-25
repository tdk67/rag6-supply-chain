"""Integration tests for tri-modal retrieval tools (SQL, Graph, Vector)."""

from retrieval.sql_query import SQLQueryTool
from retrieval.graph_query import GraphQueryTool
from retrieval.vector_search import VectorSearchTool


def test_sql_query_tool_benchmark_po():
    tool = SQLQueryTool()
    res = tool.text_to_sql_query("What is the total value of PO-8821?")
    assert res.success is True
    assert res.row_count == 1
    assert res.rows[0]["po_number"] == "PO-8821"
    assert res.rows[0]["total_val_eur"] == 1184000.0


def test_sql_query_tool_mutation_blocking():
    tool = SQLQueryTool()
    res = tool.execute_raw("DROP TABLE components;")
    assert res.success is False
    assert "Forbidden SQL" in (res.error_message or "")


def test_graph_query_tool_supplier():
    tool = GraphQueryTool()
    res = tool.query("Which supplier provides SKU-GPU-MI300X?")
    assert res.success is True
    assert res.nodes_found >= 1
    suppliers = res.data["suppliers"]
    sup_names = [s["name"] for s in suppliers]
    assert "AMD Enterprise" in sup_names


def test_graph_query_tool_single_source():
    tool = GraphQueryTool()
    res = tool.query("Which components have only one qualified supplier?")
    assert res.success is True
    spofs = res.data["single_source_components"]
    spof_skus = [s["sku"] for s in spofs]
    assert "SKU-CBL-PAM4-SPOF" in spof_skus or "SKU-SEC-HSM-SOV" in spof_skus


def test_vector_search_tool_abac():
    tool = VectorSearchTool()

    # Legal persona has clearance
    res_legal = tool.search("Liquidated damages", persona="LEGAL", target_collection="legal_contracts")
    assert res_legal.success is True
    assert res_legal.abac_blocked is False

    # SRE persona blocked from legal_contracts
    res_sre = tool.search("Liquidated damages", persona="SRE", target_collection="legal_contracts")
    assert res_sre.success is False
    assert res_sre.abac_blocked is True
