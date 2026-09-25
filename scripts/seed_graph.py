"""Knowledge Graph Compiler from SQLite SSOT.

Builds a NetworkX MultiDiGraph representing data center physical topology,
multi-tier supplier networks, software stacks, cooling dependencies, and compliance.
Saves graph to data/generated/knowledge_graph.gpickle and data/generated/knowledge_graph.json.
"""

from __future__ import annotations

import json
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


def build_knowledge_graph() -> nx.MultiDiGraph:
    cfg = load_config()
    db_path = resolve_path(cfg["paths"]["sqlite_db"])
    graph_path = resolve_path(cfg["paths"]["graph_file"])
    graph_json_path = graph_path.with_suffix(".json")
    graph_path.parent.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}. Run generate_bom.py first.")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    G = nx.MultiDiGraph()

    # 1. Facility Node
    facility_id = "Facility-DC1-Frankfurt"
    G.add_node(
        facility_id,
        label="Facility",
        name="Aethelgard DC-1 Frankfurt",
        location="Frankfurt am Main, Germany",
        jurisdiction="European Union / Germany",
    )

    # 2. Compliance Standard Nodes
    standards = [
        ("STD-BSI-C5", "BSI C5:2024", "German Federal Office for Information Security"),
        ("STD-EU-AIA", "EU AI Act (Regulation 2024/1689)", "European Artificial Intelligence Board"),
        ("STD-NIS2", "NIS2 Directive (2022/2555)", "European Union ENISA"),
        ("STD-ISO-27001", "ISO/IEC 27001:2022", "International Organization for Standardization"),
    ]
    for std_id, name, issuer in standards:
        G.add_node(std_id, label="ComplianceStandard", name=name, issuer=issuer)
        G.add_edge(facility_id, std_id, relation="CERTIFIED_UNDER")

    # 3. Cooling Loops
    cooling_loops = [
        ("Loop-A", "Primary Direct Liquid Cooling Loop Hall 1 & 2 (North)", 2),
        ("Loop-B", "Redundant Secondary Liquid Cooling Loop Hall 1 & 2 (South)", 2),
        ("Loop-DistrictHeat", "Municipal Waste Heat Exchanger to Mainova District Network", 4),
    ]
    for loop_id, desc, pumps in cooling_loops:
        G.add_node(loop_id, label="CoolingLoop", description=desc, pump_count=pumps)
        G.add_edge(loop_id, facility_id, relation="COOLED_BY")
    G.add_edge("Loop-A", "Loop-DistrictHeat", relation="EXPORTS_HEAT_TO")
    G.add_edge("Loop-B", "Loop-DistrictHeat", relation="EXPORTS_HEAT_TO")

    # 4. Software Stacks
    sw_stacks = [
        ("SW-ROCM-6.2", "AMD ROCm 6.2 AI Driver & Runtime", "6.2.0"),
        ("SW-ROCM-6.3", "AMD ROCm 6.3 Sovereign Optimized Runtime", "6.3.1"),
        ("SW-PYTORCH-2.4", "PyTorch 2.4.1 Native ROCm/CUDA", "2.4.1"),
        ("SW-CUDA-12.4", "NVIDIA CUDA Toolkit 12.4", "12.4.1"),
        ("SW-TRITON-3.0", "OpenAI Triton Compiler", "3.0.0"),
    ]
    for sw_id, name, ver in sw_stacks:
        G.add_node(sw_id, label="SoftwareStack", name=name, version=ver)

    # 5. Countries
    countries = [
        ("Taiwan", "APAC", 0),
        ("Germany", "EU", 0),
        ("France", "EU", 0),
        ("USA", "Americas", 0),
        ("South Korea", "APAC", 0),
        ("Denmark", "EU", 0),
        ("Spain", "EU", 0),
        ("Japan", "APAC", 0),
        ("China", "APAC", 1),
        ("UK", "Europe", 0),
        ("Switzerland", "Europe", 0),
        ("Norway", "Europe", 0),
    ]
    for c_name, region, sanctioned in countries:
        c_id = f"Country-{c_name.replace(' ', '_')}"
        G.add_node(c_id, label="Country", name=c_name, region=region, sanctioned=sanctioned)

    # 6. Tenants
    for t in range(1, 7):
        t_id = f"Tenant-{t}"
        G.add_node(t_id, label="Tenant", name=f"Sovereign Tenant {t}", tier="Tier-IV-MissionCritical")

    # 7. Suppliers & SubTierManufacturers
    suppliers = cursor.execute("SELECT * FROM suppliers").fetchall()
    for s in suppliers:
        s_id = s["supplier_id"]
        G.add_node(
            s_id,
            label="Supplier",
            name=s["name"],
            country=s["country"],
            tier=s["tier"],
            status=s["status"],
            bsi_c5_certified=bool(s["bsi_c5_certified"]),
        )
        c_node = f"Country-{s['country'].replace(' ', '_')}"
        if c_node in G:
            G.add_edge(s_id, c_node, relation="LOCATED_IN")

        if s["bsi_c5_certified"]:
            G.add_edge(s_id, "STD-BSI-C5", relation="CERTIFIED_UNDER")

    # 8. Components
    components = cursor.execute("SELECT * FROM components").fetchall()
    sub_tiers_seen = set()

    for comp in components:
        c_sku = comp["sku"]
        G.add_node(
            c_sku,
            label="Component",
            sku=c_sku,
            part_name=comp["part_name"],
            category=comp["category"],
            unit_cost_eur=comp["unit_cost_eur"],
            lead_time_weeks=comp["lead_time_weeks"],
            safety_stock=comp["safety_stock"],
            current_stock=comp["current_stock"],
            moq=comp["moq"],
            ocp_compliant=bool(comp["ocp_compliant"]),
        )

        # Supplied by Tier-1
        sup1 = comp["tier1_supplier_id"]
        if sup1 in G:
            G.add_edge(c_sku, sup1, relation="SUPPLIED_BY")

        # SubTierManufacturer
        sub_name = comp["tier2_manufacturer"]
        sub_id = f"SubTier-{sub_name.replace(' ', '_')}"
        if sub_id not in sub_tiers_seen:
            sub_country = "Taiwan" if "Taiwan" in sub_name or "TSMC" in sub_name or "Foxconn" in sub_name else "Germany"
            if "France" in sub_name or "STMicro" in sub_name:
                sub_country = "France"
            elif "Hynix" in sub_name or "Samsung" in sub_name:
                sub_country = "South Korea"
            elif "Micron" in sub_name:
                sub_country = "USA"
            elif "Danfoss" in sub_name:
                sub_country = "Denmark"

            G.add_node(sub_id, label="SubTierManufacturer", name=sub_name, country=sub_country)
            c_node = f"Country-{sub_country.replace(' ', '_')}"
            if c_node in G:
                G.add_edge(sub_id, c_node, relation="LOCATED_IN")
            sub_tiers_seen.add(sub_id)

        G.add_edge(sup1, sub_id, relation="SUBCONTRACTS_TO")
        G.add_edge(c_sku, sub_id, relation="MANUFACTURED_BY")

        # Fabricated in Country
        fab_country = comp["country_of_origin"]
        fab_node = f"Country-{fab_country.replace(' ', '_')}"
        if fab_node in G:
            G.add_edge(c_sku, fab_node, relation="FABRICATED_IN")

        # Software stack compatibility
        if comp["category"] == "GPU":
            if "MI300X" in c_sku or "AMD" in comp["part_name"]:
                G.add_edge(c_sku, "SW-ROCM-6.2", relation="COMPATIBLE_WITH")
                G.add_edge(c_sku, "SW-ROCM-6.3", relation="COMPATIBLE_WITH")
                G.add_edge(c_sku, "SW-PYTORCH-2.4", relation="COMPATIBLE_WITH")
            elif "H200" in c_sku or "NVIDIA" in comp["part_name"]:
                G.add_edge(c_sku, "SW-CUDA-12.4", relation="COMPATIBLE_WITH")
                G.add_edge(c_sku, "SW-PYTORCH-2.4", relation="COMPATIBLE_WITH")
        elif comp["category"] == "Switch":
            G.add_edge(c_sku, "SW-TRITON-3.0", relation="COMPATIBLE_WITH")

    # Add secondary supplier edges for multi-sourced components (keeping single-source for SPOF components!)
    single_source_skus = {"SKU-CBL-PAM4-SPOF", "SKU-SEC-HSM-SOV"}
    all_tier1_sups = [s["supplier_id"] for s in suppliers if s["tier"] == "Tier-1"]

    for comp in components:
        sku = comp["sku"]
        if sku not in single_source_skus:
            # 65% of components have a secondary qualified supplier
            if hash(sku) % 100 < 65:
                alt_sup = all_tier1_sups[(hash(sku) // 100) % len(all_tier1_sups)]
                if alt_sup != comp["tier1_supplier_id"]:
                    G.add_edge(sku, alt_sup, relation="SUPPLIED_BY", role="SECONDARY")

    # 9. Racks & Chassis
    racks = cursor.execute("SELECT * FROM racks").fetchall()
    gpu_skus = [c["sku"] for c in components if c["category"] == "GPU"]
    cpu_skus = [c["sku"] for c in components if c["category"] == "CPU"]
    psu_skus = [c["sku"] for c in components if c["category"] == "PSU"]
    trans_skus = [c["sku"] for c in components if c["category"] == "Transceiver"]
    man_skus = [c["sku"] for c in components if c["category"] == "Manifold"]
    switch_skus = [c["sku"] for c in components if c["category"] == "Switch"]

    for r in racks:
        r_id = r["rack_id"]
        G.add_node(
            r_id,
            label="Rack",
            rack_id=r_id,
            hall=r["hall"],
            power_kw=r["power_kw"],
            cooling_loop=r["cooling_loop"],
            gpu_type=r["gpu_type"],
            status=r["status"],
        )
        G.add_edge(r_id, facility_id, relation="LOCATED_IN")
        G.add_edge(r_id, r["cooling_loop"], relation="COOLED_BY")
        
        # Link to Tenant
        t_id = f"Tenant-{((int(r_id.split('-')[1])-1) % 6) + 1}"
        G.add_edge(r_id, t_id, relation="SERVES_TENANT")

        # Chassis inside rack
        chassis_id = f"Chassis-{r_id}"
        G.add_node(chassis_id, label="Chassis", rack_id=r_id, ocp_standard="ORV3-44OU")
        G.add_edge(r_id, chassis_id, relation="CONTAINS")

        # Link physical components into Chassis
        # Assign GPU SKU
        selected_gpu = "SKU-GPU-MI300X" if "MI300X" in r["gpu_type"] else "SKU-GPU-H200"
        G.add_edge(chassis_id, selected_gpu, relation="CONTAINS", quantity=8)
        
        # Assign chassis sled
        sled_sku = "SKU-CHAS-ORV3-SM" if selected_gpu == "SKU-GPU-MI300X" else "SKU-CHAS-ORV3-WI"
        G.add_edge(chassis_id, sled_sku, relation="CONTAINS", quantity=1)

        # Assign PSU, Manifold, Switch, Transceiver
        G.add_edge(chassis_id, psu_skus[int(r_id.split('-')[1]) % len(psu_skus)], relation="CONTAINS", quantity=2)
        G.add_edge(chassis_id, man_skus[int(r_id.split('-')[1]) % len(man_skus)], relation="CONTAINS", quantity=1)
        G.add_edge(chassis_id, switch_skus[int(r_id.split('-')[1]) % len(switch_skus)], relation="CONTAINS", quantity=2)
        G.add_edge(chassis_id, trans_skus[int(r_id.split('-')[1]) % len(trans_skus)], relation="CONTAINS", quantity=16)

    # 10. Cooling Loop to Pump Component relationships
    G.add_edge("Loop-A", "SKU-PUMP-HALL1-B", relation="DEPENDS_ON_PUMP")
    G.add_edge("Loop-B", "SKU-PUMP-HALL2-A", relation="DEPENDS_ON_PUMP")

    conn.close()

    # Save Graph as secure node-link JSON (zero pickle vulnerabilities)
    node_link_data = nx.node_link_data(G)
    with open(graph_json_path, "w", encoding="utf-8") as f:
        json.dump(node_link_data, f, indent=2)

    # Optional legacy pickle compatibility file
    with open(graph_path, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Knowledge Graph successfully built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    print(f"Graph safely serialized to JSON: {graph_json_path}")
    return G


if __name__ == "__main__":
    build_knowledge_graph()
