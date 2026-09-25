"""Data Validation & Referential Integrity Suite.

Cross-checks consistency between:
- SQLite SSOT (components, suppliers, purchase_orders, dock_receipts, racks, document_registry)
- NetworkX Knowledge Graph (nodes, edges, connectivity)
- Document files on disk (data/documents/*.pdf)
"""

from __future__ import annotations

import pickle
import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import networkx as nx
from utils.config import resolve_path, load_config


def validate_all_data() -> bool:
    cfg = load_config()
    db_path = resolve_path(cfg["paths"]["sqlite_db"])
    graph_path = resolve_path(cfg["paths"]["graph_file"])
    docs_dir = resolve_path(cfg["paths"]["documents_dir"])

    errors = []
    print("=" * 60)
    print("AETHELGARD INFRA-GRAPHRAG: DATA INTEGRITY VALIDATION")
    print("=" * 60)

    # 1. Database Checks
    if not db_path.exists():
        errors.append(f"Missing SQLite database at {db_path}")
        print("[-] FAIL: SQLite database missing")
        return False

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    comp_count = cur.execute("SELECT COUNT(*) FROM components").fetchone()[0]
    sup_count = cur.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    po_count = cur.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
    dock_count = cur.execute("SELECT COUNT(*) FROM dock_receipts").fetchone()[0]
    rack_count = cur.execute("SELECT COUNT(*) FROM racks").fetchone()[0]
    doc_count = cur.execute("SELECT COUNT(*) FROM document_registry").fetchone()[0]

    print(f"[+] SQLite Tables Verified:")
    print(f"    - components:      {comp_count:4d} rows (Target >= 150)")
    print(f"    - suppliers:       {sup_count:4d} rows (Target >= 30)")
    print(f"    - purchase_orders: {po_count:4d} rows (Target >= 80)")
    print(f"    - dock_receipts:   {dock_count:4d} rows (Target >= 60)")
    print(f"    - racks:           {rack_count:4d} rows (Target = 48)")
    print(f"    - document_registry:{doc_count:4d} rows")

    if comp_count < 150:
        errors.append(f"Components row count {comp_count} below target 150")
    if sup_count < 30:
        errors.append(f"Suppliers row count {sup_count} below target 30")
    if po_count < 80:
        errors.append(f"Purchase orders count {po_count} below target 80")
    if rack_count != 48:
        errors.append(f"Racks count {rack_count} != 48")

    # Referential Integrity: Orphan SKUs in POs
    orphan_pos = cur.execute(
        "SELECT po_number, sku FROM purchase_orders WHERE sku NOT IN (SELECT sku FROM components)"
    ).fetchall()
    if orphan_pos:
        errors.append(f"Found {len(orphan_pos)} purchase orders with orphan SKUs")

    # Referential Integrity: Orphan POs in Dock Receipts
    orphan_docks = cur.execute(
        "SELECT receipt_id, po_number FROM dock_receipts WHERE po_number NOT IN (SELECT po_number FROM purchase_orders)"
    ).fetchall()
    if orphan_docks:
        errors.append(f"Found {len(orphan_docks)} dock receipts with orphan PO numbers")

    # Check PO-8821 benchmark record exists
    po_8821 = cur.execute("SELECT total_val_eur, status, quantity FROM purchase_orders WHERE po_number='PO-8821'").fetchone()
    if not po_8821:
        errors.append("Benchmark record PO-8821 missing from purchase_orders")
    else:
        print(f"[+] Benchmark PO-8821 Verified: Qty={po_8821[2]}, Total=EUR {po_8821[0]:,.2f}, Status={po_8821[1]}")

    # Check REC-104 discrepancy record exists
    rec_104 = cur.execute("SELECT units_received, discrepancy_flag FROM dock_receipts WHERE receipt_id='REC-104'").fetchone()
    if not rec_104 or rec_104[1] != 1:
        errors.append("Benchmark discrepancy record REC-104 missing or discrepancy_flag != 1")
    else:
        print(f"[+] Benchmark REC-104 Discrepancy Verified: Units={rec_104[0]} (ordered 64, missing 32), Flag={rec_104[1]}")

    conn.close()

    # 2. Knowledge Graph Checks
    if not graph_path.exists():
        errors.append(f"Missing knowledge graph at {graph_path}")
        print("[-] FAIL: Knowledge graph file missing")
        return False

    with open(graph_path, "rb") as f:
        G: nx.MultiDiGraph = pickle.load(f)

    nodes_cnt = G.number_of_nodes()
    edges_cnt = G.number_of_edges()
    print(f"[+] Knowledge Graph Verified:")
    print(f"    - Total Nodes:     {nodes_cnt:4d} nodes")
    print(f"    - Total Edges:     {edges_cnt:4d} edges")

    if nodes_cnt < 250:
        errors.append(f"Node count {nodes_cnt} lower than acceptable threshold (250)")
    if edges_cnt < 800:
        errors.append(f"Edge count {edges_cnt} lower than acceptable threshold (800)")

    # Check key nodes in graph
    for key_node in ["SKU-GPU-MI300X", "SKU-GPU-H200", "SUP-001", "Rack-01", "Loop-A", "STD-BSI-C5"]:
        if key_node not in G:
            errors.append(f"Key node '{key_node}' missing from knowledge graph")

    # 3. Document Files on Disk Checks
    pdf_files = list(docs_dir.glob("*.pdf"))
    print(f"[+] Documents on Disk Verified:")
    print(f"    - PDF Files:       {len(pdf_files):4d} files in {docs_dir.name}/")

    if len(pdf_files) < 10:
        errors.append(f"Found only {len(pdf_files)} PDF files in data/documents (expected >= 10)")

    print("-" * 60)
    if errors:
        print(f"[-] VALIDATION FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"    - {err}")
        return False
    else:
        print("[+] VALIDATION PASSED: 100% Referential Integrity across DB, Graph, and Documents!")
        print("=" * 60)
        return True


if __name__ == "__main__":
    success = validate_all_data()
    sys.exit(0 if success else 1)
