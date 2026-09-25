"""Synthetic Bill of Materials (BOM) & Inventory Database Generator.

Generates:
1. SQLite database at data/generated/infrastructure.db with SSOT schema:
   - components (150+ SKUs, OCP-compliant, pricing in EUR)
   - suppliers (30+ vendors across Tier-1/2/3, countries, compliance flags)
   - purchase_orders (80+ records including PO-8821 benchmark record)
   - dock_receipts (60+ records with intentional discrepancy rows like REC-104)
   - racks (48 racks across Hall 1 and Hall 2)
   - document_registry (tracks document lifecycle, versions, hashes)
2. Excel workbook export at data/generated/bom_inventory.xlsx with all tables.
"""

from __future__ import annotations

import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from utils.config import resolve_path, load_config

# Set deterministic seed for reproducible datasets
random.seed(42)

def generate_bom_data():
    cfg = load_config()
    db_path = resolve_path(cfg["paths"]["sqlite_db"])
    excel_path = resolve_path(cfg["paths"]["bom_excel"])
    
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    excel_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Create tables
    cursor.executescript("""
    CREATE TABLE suppliers (
        supplier_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        country TEXT NOT NULL,
        tier TEXT NOT NULL,
        status TEXT NOT NULL,
        bsi_c5_certified INTEGER NOT NULL
    );

    CREATE TABLE components (
        sku TEXT PRIMARY KEY,
        part_name TEXT NOT NULL,
        category TEXT NOT NULL,
        tier1_supplier_id TEXT NOT NULL,
        tier2_manufacturer TEXT NOT NULL,
        country_of_origin TEXT NOT NULL,
        unit_cost_eur REAL NOT NULL,
        lead_time_weeks INTEGER NOT NULL,
        safety_stock INTEGER NOT NULL,
        current_stock INTEGER NOT NULL,
        moq INTEGER NOT NULL,
        ocp_compliant INTEGER NOT NULL,
        FOREIGN KEY (tier1_supplier_id) REFERENCES suppliers(supplier_id)
    );

    CREATE TABLE purchase_orders (
        po_number TEXT PRIMARY KEY,
        sku TEXT NOT NULL,
        supplier_id TEXT NOT NULL,
        order_date TEXT NOT NULL,
        agreed_delivery_date TEXT NOT NULL,
        actual_delivery_date TEXT,
        status TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        total_val_eur REAL NOT NULL,
        FOREIGN KEY (sku) REFERENCES components(sku),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    );

    CREATE TABLE dock_receipts (
        receipt_id TEXT PRIMARY KEY,
        po_number TEXT NOT NULL,
        units_received INTEGER NOT NULL,
        received_date TEXT NOT NULL,
        serial_numbers TEXT,
        discrepancy_flag INTEGER NOT NULL,
        discrepancy_notes TEXT,
        FOREIGN KEY (po_number) REFERENCES purchase_orders(po_number)
    );

    CREATE TABLE racks (
        rack_id TEXT PRIMARY KEY,
        hall TEXT NOT NULL,
        power_kw REAL NOT NULL,
        cooling_loop TEXT NOT NULL,
        gpu_type TEXT NOT NULL,
        status TEXT NOT NULL,
        customer_tenant TEXT NOT NULL
    );

    CREATE TABLE document_registry (
        doc_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        version TEXT NOT NULL,
        effective_date TEXT NOT NULL,
        is_active INTEGER NOT NULL,
        classification TEXT NOT NULL,
        sha256_hash TEXT NOT NULL,
        total_pages INTEGER NOT NULL,
        total_chunks INTEGER NOT NULL,
        deprecated_at TEXT,
        replaced_by TEXT,
        ingested_at TEXT NOT NULL
    );
    """)

    # 2. Seed Suppliers (32 suppliers)
    suppliers_data = [
        # Key Tier-1 vendors from PRD
        ("SUP-001", "Supermicro", "USA", "Tier-1", "ACTIVE", 1),
        ("SUP-002", "Wiwynn Corporation", "Taiwan", "Tier-1", "ACTIVE", 1),
        ("SUP-003", "Eviden / BullSequana", "France", "Tier-1", "ACTIVE", 1),
        ("SUP-004", "Submer Liquid Cooling", "Spain", "Tier-1", "ACTIVE", 1),
        ("SUP-005", "Broadcom", "USA", "Tier-1", "ACTIVE", 1),
        ("SUP-006", "Molex Datacom", "Germany", "Tier-1", "ACTIVE", 1),
        ("SUP-007", "Delta Electronics", "Taiwan", "Tier-1", "ACTIVE", 0),
        ("SUP-008", "Schneider Electric", "France", "Tier-1", "ACTIVE", 1),
        ("SUP-009", "AMD Enterprise", "USA", "Tier-1", "ACTIVE", 1),
        ("SUP-010", "NVIDIA Corporation", "USA", "Tier-1", "ACTIVE", 1),
        # Upstream Tier-2 / Tier-3 and regional suppliers
        ("SUP-011", "TSMC Semiconductor", "Taiwan", "Tier-3", "ACTIVE", 1),
        ("SUP-012", "Foxconn Industrial", "Taiwan", "Tier-2", "ACTIVE", 0),
        ("SUP-013", "Quanta Cloud Technology", "Taiwan", "Tier-1", "ACTIVE", 1),
        ("SUP-014", "Infineon Technologies", "Germany", "Tier-2", "ACTIVE", 1),
        ("SUP-015", "STMicroelectronics", "France", "Tier-2", "ACTIVE", 1),
        ("SUP-016", "SK Hynix", "South Korea", "Tier-2", "ACTIVE", 1),
        ("SUP-017", "Samsung Electronics", "South Korea", "Tier-2", "ACTIVE", 1),
        ("SUP-018", "Micron Technology", "USA", "Tier-2", "ACTIVE", 1),
        ("SUP-019", "Rittal GmbH", "Germany", "Tier-1", "ACTIVE", 1),
        ("SUP-020", "Danfoss Climate Solutions", "Denmark", "Tier-2", "ACTIVE", 1),
        ("SUP-021", "Amphenol Communications", "USA", "Tier-2", "ACTIVE", 1),
        ("SUP-022", "Shenzhen Luxshare-ICT", "China", "Tier-2", "ACTIVE", 0),
        ("SUP-023", "Asus Cloud Servers", "Taiwan", "Tier-1", "ACTIVE", 0),
        ("SUP-024", "Inspur Systems", "China", "Tier-1", "SANCTIONED", 0),
        ("SUP-025", "Nidec Motor Corp", "Japan", "Tier-2", "ACTIVE", 1),
        ("SUP-026", "Asetek Liquid Cooling", "Denmark", "Tier-1", "ACTIVE", 1),
        ("SUP-027", "Volex Power Cables", "UK", "Tier-2", "ACTIVE", 1),
        ("SUP-028", "Huber+Suhner Fiber", "Switzerland", "Tier-1", "ACTIVE", 1),
        ("SUP-029", "Silicon Integrated Systems", "Taiwan", "Tier-3", "ACTIVE", 0),
        ("SUP-030", "Nordic Semiconductor", "Norway", "Tier-2", "ACTIVE", 1),
        ("SUP-031", "Cooler Master Corp", "Taiwan", "Tier-2", "ACTIVE", 0),
        ("SUP-032", "Kelvion Heat Exchangers", "Germany", "Tier-2", "ACTIVE", 1)
    ]
    cursor.executemany("INSERT INTO suppliers VALUES (?,?,?,?,?,?)", suppliers_data)

    # 3. Seed Components (155 SKUs)
    categories = ["GPU", "CPU", "Transceiver", "Manifold", "PSU", "Memory", "Storage", "Switch", "Busbar", "CoolingPump"]
    
    # Priority benchmark components explicitly defined
    explicit_components = [
        # (sku, name, cat, sup1, sup2, country, cost, lead_w, safety, stock, moq, ocp)
        ("SKU-GPU-MI300X", "AMD Instinct MI300X 192GB OAM", "GPU", "SUP-009", "TSMC Semiconductor", "Taiwan", 14500.0, 18, 20, 48, 8, 1),
        ("SKU-GPU-H200", "NVIDIA H200 SXM5 141GB", "GPU", "SUP-010", "TSMC Semiconductor", "Taiwan", 28000.0, 32, 10, 24, 8, 0),
        ("SKU-CHAS-ORV3-SM", "Supermicro ORV3 8U GPU Chassis Module", "GPU", "SUP-001", "Foxconn Industrial", "Taiwan", 18500.0, 14, 16, 32, 4, 1),
        ("SKU-CHAS-ORV3-WI", "Wiwynn ORV3 4OU Compute Sled", "CPU", "SUP-002", "Quanta Cloud Technology", "Taiwan", 9200.0, 12, 24, 56, 4, 1),
        ("SKU-CHAS-EVIDEN-BULL", "Eviden BullSequana XH3000 Blade", "CPU", "SUP-003", "STMicroelectronics", "France", 22000.0, 16, 12, 20, 2, 1),
        ("SKU-OPT-800G", "Broadcom Tomahawk 5 800G OSFP Optical Transceiver", "Transceiver", "SUP-005", "TSMC Semiconductor", "Taiwan", 850.0, 20, 100, 180, 16, 1),
        ("SKU-OPT-800G-MOL", "Molex 800G OSFP DR8 European Transceiver", "Transceiver", "SUP-006", "Infineon Technologies", "Germany", 920.0, 8, 80, 210, 16, 1),
        ("SKU-SW-TH5", "Broadcom Tomahawk 5 64-port 800GbE Spine Switch", "Switch", "SUP-005", "TSMC Semiconductor", "Taiwan", 42000.0, 24, 6, 12, 1, 1),
        ("SKU-MAN-SUBMER-01", "Submer SmartPod Immersion Cooling Manifold v3", "Manifold", "SUP-004", "Danfoss Climate Solutions", "Spain", 12500.0, 16, 8, 14, 2, 1),
        ("SKU-MAN-ASETEK-02", "Asetek Direct-to-Chip Quick-Disconnect Manifold", "Manifold", "SUP-026", "Danfoss Climate Solutions", "Denmark", 11200.0, 10, 12, 28, 2, 1),
        ("SKU-PSU-ORV3-48V", "Delta 33kW 48V OCP Power Shelf Busbar PSU", "PSU", "SUP-007", "Infineon Technologies", "Taiwan", 6800.0, 14, 16, 30, 2, 1),
        ("SKU-PSU-SCHN-48V", "Schneider Galaxy 48V High-Efficiency Power Module", "PSU", "SUP-008", "STMicroelectronics", "France", 7400.0, 8, 18, 42, 2, 1),
        ("SKU-PUMP-HALL1-B", "Danfoss MagDrive Primary Coolant Pump 500L/min", "CoolingPump", "SUP-020", "Danfoss Climate Solutions", "Denmark", 15800.0, 12, 4, 6, 1, 1),
        ("SKU-PUMP-HALL2-A", "Kelvion Industrial DC Glycol Circulator", "CoolingPump", "SUP-032", "Kelvion Heat Exchangers", "Germany", 16200.0, 10, 4, 8, 1, 1),
        ("SKU-MEM-HBM3E", "SK Hynix 24GB HBM3e High Bandwidth Memory Stack", "Memory", "SUP-016", "SK Hynix", "South Korea", 620.0, 16, 200, 450, 32, 1),
        ("SKU-MEM-DDR5-REG", "Samsung 64GB DDR5-5600 Registered ECC DIMM", "Memory", "SUP-017", "Samsung Electronics", "South Korea", 280.0, 6, 300, 820, 32, 1),
        ("SKU-STOR-E1S-8TB", "Solidigm E1.S 7.68TB NVMe PCIe 5.0 SSD", "Storage", "SUP-018", "Micron Technology", "USA", 890.0, 8, 120, 240, 10, 1),
        ("SKU-BUS-ORV3-COP", "Rittal ORV3 Solid Copper 48V Power Busbar 2000A", "Busbar", "SUP-019", "Rittal GmbH", "Germany", 2400.0, 6, 20, 44, 4, 1),
        # Single-source components (crucial for Benchmark Q3)
        ("SKU-CBL-PAM4-SPOF", "Amphenol ExaMAX+ Ultra-Dense PAM4 Backplane Harness", "Busbar", "SUP-021", "Amphenol Communications", "USA", 1850.0, 26, 4, 8, 2, 1),
        ("SKU-SEC-HSM-SOV", "Eviden Trustway Sovereign Hardware Security Module PCIe", "Switch", "SUP-003", "STMicroelectronics", "France", 18900.0, 14, 5, 10, 1, 1)
    ]

    components_list = list(explicit_components)
    tier1_sup_ids = [s[0] for s in suppliers_data if s[3] == "Tier-1"]
    tier2_names = [s[1] for s in suppliers_data if s[3] in ("Tier-2", "Tier-3")]
    countries = ["Taiwan", "Germany", "France", "USA", "South Korea", "Denmark", "Spain", "Japan"]

    # Generate additional SKUs to reach 155 total
    for i in range(len(components_list) + 1, 156):
        cat = categories[i % len(categories)]
        sku = f"SKU-{cat[:3].upper()}-{i:04d}"
        part_name = f"Enterprise {cat} Subsystem Series-{i*7 % 900 + 100}"
        sup1 = random.choice(tier1_sup_ids)
        sup2 = random.choice(tier2_names)
        country = random.choice(countries)
        
        # Base pricing per category
        base_costs = {
            "GPU": 12000.0, "CPU": 4500.0, "Transceiver": 700.0, "Manifold": 9000.0,
            "PSU": 4800.0, "Memory": 350.0, "Storage": 600.0, "Switch": 25000.0,
            "Busbar": 1800.0, "CoolingPump": 13000.0
        }
        cost = round(base_costs[cat] * random.uniform(0.7, 1.4), 2)
        lead_time = random.randint(4, 24)
        safety = random.randint(8, 60)
        stock = random.randint(safety, safety * 3)
        moq = random.choice([1, 2, 4, 8, 16])
        ocp = 1 if random.random() > 0.25 else 0

        components_list.append((sku, part_name, cat, sup1, sup2, country, cost, lead_time, safety, stock, moq, ocp))

    cursor.executemany("INSERT INTO components VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", components_list)

    # 4. Seed Purchase Orders (85 POs)
    # Important benchmark record PO-8821
    po_list = [
        ("PO-8821", "SKU-CHAS-ORV3-SM", "SUP-001", "2025-11-10", "2026-01-15", None, "DELAYED", 64, 1184000.00),
        ("PO-8822", "SKU-GPU-MI300X", "SUP-009", "2025-12-01", "2026-02-15", "2026-02-14", "DELIVERED", 48, 696000.00),
        ("PO-8823", "SKU-OPT-800G", "SUP-005", "2026-01-10", "2026-04-10", None, "OPEN", 128, 108800.00),
        ("PO-8824", "SKU-MAN-SUBMER-01", "SUP-004", "2026-01-05", "2026-03-20", None, "OPEN", 8, 100000.00),
        ("PO-8825", "SKU-SW-TH5", "SUP-005", "2025-10-15", "2026-01-30", "2026-01-28", "DELIVERED", 8, 336000.00),
        ("PO-8826", "SKU-PSU-ORV3-48V", "SUP-007", "2026-01-12", "2026-03-30", None, "OPEN", 24, 163200.00),
        ("PO-8827", "SKU-CHAS-ORV3-WI", "SUP-002", "2025-11-20", "2026-02-10", "2026-02-08", "DELIVERED", 32, 294400.00),
        ("PO-8828", "SKU-PUMP-HALL1-B", "SUP-020", "2025-09-01", "2025-11-15", "2025-11-14", "DELIVERED", 4, 63200.00),
        ("PO-8829", "SKU-CBL-PAM4-SPOF", "SUP-021", "2026-01-20", "2026-07-25", None, "OPEN", 16, 29600.00),
        ("PO-8830", "SKU-SEC-HSM-SOV", "SUP-003", "2025-12-15", "2026-03-01", None, "OPEN", 10, 189000.00),
    ]

    base_date = datetime(2025, 9, 1, tzinfo=timezone.utc)
    for i in range(11, 86):
        po_num = f"PO-{8820 + i}"
        comp = random.choice(components_list)
        sku = comp[0]
        sup_id = comp[3]
        unit_cost = comp[6]
        qty = random.choice([4, 8, 12, 16, 24, 32, 64, 128])
        total_val = round(unit_cost * qty, 2)
        
        ord_date = base_date + timedelta(days=random.randint(0, 150))
        agreed_date = ord_date + timedelta(weeks=random.randint(6, 20))
        status = random.choice(["OPEN", "DELIVERED", "DELAYED", "OPEN", "DELIVERED"])
        actual_date = agreed_date.strftime("%Y-%m-%d") if status == "DELIVERED" else None

        po_list.append((po_num, sku, sup_id, ord_date.strftime("%Y-%m-%d"), agreed_date.strftime("%Y-%m-%d"), actual_date, status, qty, total_val))

    cursor.executemany("INSERT INTO purchase_orders VALUES (?,?,?,?,?,?,?,?,?)", po_list)

    # 5. Seed Dock Receipts (65 receipts)
    # Notice REC-104 intentional discrepancy with PO-8821 (Trap 2 mitigation!)
    dock_receipts = [
        ("REC-104", "PO-8821", 32, "2026-01-22", "SN-SM-8821-001..032", 1, "Discrepancy: PO-8821 specified 64 units of SKU-CHAS-ORV3-SM; only 32 units arrived on manifest. 32 units backordered."),
        ("REC-105", "PO-8822", 48, "2026-02-14", "SN-MI300X-4801..4848", 0, "Inspected and accepted into Hall 1 Cold Storage"),
        ("REC-106", "PO-8825", 8, "2026-01-28", "SN-TH5-001..008", 0, "Passed optical self-test. Firmware 6.2 loaded"),
        ("REC-107", "PO-8827", 32, "2026-02-08", "SN-WI-2026-01..32", 0, "Inspected, zero cosmetic damage"),
        ("REC-108", "PO-8828", 4, "2025-11-14", "SN-DANF-500L-01..04", 0, "Hydraulic pressure testing certified"),
    ]

    for i in range(1, 61):
        rec_id = f"REC-{120 + i}"
        # Pick from delivered or delayed POs
        eligible_pos = [p for p in po_list if p[6] in ("DELIVERED", "DELAYED")]
        target_po = random.choice(eligible_pos)
        po_num = target_po[0]
        qty_ordered = target_po[7]
        
        # 10% chance of small discrepancy
        has_disc = 1 if (random.random() < 0.12) else 0
        units = qty_ordered if has_disc == 0 else max(1, qty_ordered - random.randint(1, 4))
        notes = f"Discrepancy: Expected {qty_ordered}, received {units} units." if has_disc else "Verified and received into inventory."
        
        dock_receipts.append((rec_id, po_num, units, "2026-02-01", f"SN-{rec_id}-BATCH", has_disc, notes))

    cursor.executemany("INSERT INTO dock_receipts VALUES (?,?,?,?,?,?,?)", dock_receipts)

    # 6. Seed Racks (48 Racks in DC-1 Frankfurt)
    racks_data = []
    # Racks 1-24 in Hall 1, 25-48 in Hall 2
    for r in range(1, 49):
        rack_id = f"Rack-{r:02d}"
        hall = "Hall 1" if r <= 24 else "Hall 2"
        power_kw = round(random.uniform(32.0, 48.0), 1)
        # Hall 1 has Loop-A and Loop-B; Loop-A cooling pumps are SKU-PUMP-HALL1-B
        cooling_loop = "Loop-A" if (r <= 12 or (25 <= r <= 36)) else "Loop-B"
        gpu_type = "AMD Instinct MI300X" if r % 2 == 1 else "NVIDIA H200"
        status = "OPERATIONAL" if r not in (13, 14) else "MAINTENANCE"
        tenant = f"Sovereign-Tenant-{((r-1)%6)+1}"
        racks_data.append((rack_id, hall, power_kw, cooling_loop, gpu_type, status, tenant))

    cursor.executemany("INSERT INTO racks VALUES (?,?,?,?,?,?,?)", racks_data)

    # 7. Seed Document Registry (initial records)
    initial_docs = [
        ("doc-msa-supermicro", "Supermicro Master Service Agreement 2026", "Supermicro_GPU_Nodes_MSA.pdf", "1.2", "2026-01-15", 1, "LEGAL_COMMERCIAL", "a3f8c2e104b2c129e87740df98a", 42, 87, None, None, "2026-01-16T10:30:00Z"),
        ("doc-msa-wiwynn", "Wiwynn Chassis & Rack Supply Agreement", "Wiwynn_Chassis_MSA.pdf", "1.0", "2025-11-01", 1, "LEGAL_COMMERCIAL", "c4b9d8e723a1f4901e8372cb71a", 38, 76, None, None, "2025-11-05T09:15:00Z"),
        ("doc-msa-eviden", "Eviden BullSequana High Performance Server Contract", "Eviden_BullSequana_Contract.pdf", "2.1", "2025-12-10", 1, "LEGAL_COMMERCIAL", "e9f0a1c3d5b78294716028ef43b", 50, 102, None, None, "2025-12-12T14:20:00Z"),
        ("doc-msa-submer", "Submer Immersion Cooling Systems SLA", "Submer_Cooling_Agreement.pdf", "1.1", "2025-10-15", 1, "LEGAL_COMMERCIAL", "f1b2c3d4e5f60718293a4b5c6d7", 32, 64, None, None, "2025-10-18T11:00:00Z"),
        ("doc-spec-ocp-orv3", "OCP Open Rack v3 Mechanical & Power Spec", "OCP_ORV3_Rack_Standard.pdf", "3.0", "2025-06-01", 1, "TECHNICAL_SPEC", "12a34b56c78d90ef123456789ab", 64, 120, None, None, "2025-06-10T08:00:00Z"),
        ("doc-spec-amd-mi300x", "AMD Instinct MI300X Accelerator Architecture & Deployment Guide", "AMD_MI300X_Deployment_Guide.pdf", "1.4", "2025-09-01", 1, "TECHNICAL_SPEC", "78d90ef123456789ab12a34b56c", 82, 160, None, None, "2025-09-15T16:00:00Z"),
        ("doc-spec-rocev2", "RoCEv2 800G Data Center Fabric Architecture", "RoCEv2_Network_Fabric_Spec.pdf", "2.0", "2025-08-20", 1, "TECHNICAL_SPEC", "456789ab12a34b56c78d90ef123", 46, 92, None, None, "2025-08-25T13:45:00Z"),
        ("doc-comp-bsi-c5", "BSI C5 Sovereign Cloud Security & Attestation Criteria", "BSI_C5_Sovereignty_Attestation.pdf", "2024.1", "2025-01-10", 1, "COMPLIANCE_AUDIT", "90ef123456789ab12a34b56c78d", 54, 110, None, None, "2025-01-20T10:00:00Z"),
        ("doc-comp-eu-ai-act", "EU AI Act Sovereign Compute Compliance Whitepaper", "EU_AI_Act_Conformity_Statement.pdf", "1.0", "2025-07-01", 1, "COMPLIANCE_AUDIT", "ef123456789ab12a34b56c78d90", 35, 70, None, None, "2025-07-10T15:30:00Z"),
        ("doc-comp-nis2", "NIS2 Critical Infrastructure Security Standard & Audit", "NIS2_Supply_Chain_Security_Policy.pdf", "1.0", "2025-05-15", 1, "COMPLIANCE_AUDIT", "56c78d90ef123456789ab12a34b", 28, 55, None, None, "2025-05-20T12:00:00Z"),
        ("doc-disr-taiwan", "Geopolitical Freight Risk Advisory: Taiwan Strait Transit", "Taiwan_Strait_Freight_Advisory.pdf", "1.0", "2026-01-20", 1, "DISRUPTION_BULLETIN", "23456789ab12a34b56c78d90ef1", 12, 24, None, None, "2026-01-22T08:30:00Z"),
        ("doc-disr-redsea", "Maritime Shipping Disruption Analysis: Suez & Red Sea", "Red_Sea_Shipping_Disruption_Report.pdf", "1.0", "2026-01-05", 1, "DISRUPTION_BULLETIN", "3456789ab12a34b56c78d90ef12", 15, 30, None, None, "2026-01-08T11:20:00Z"),
        ("doc-ppa-district-heat", "Frankfurt Municipal District Heating Waste Heat Export PPA", "District_Heating_PPA.pdf", "1.0", "2025-04-01", 1, "LEGAL_COMMERCIAL", "bc78d90ef123456789ab12a3456", 24, 48, None, None, "2025-04-10T09:00:00Z"),
        ("doc-disr-us-export", "US BIS Advanced Compute Export Controls Regulatory Briefing", "US_Export_Control_Update.pdf", "1.0", "2025-10-30", 1, "DISRUPTION_BULLETIN", "de789ab12a34b56c78d90ef1234", 18, 36, None, None, "2025-11-02T14:00:00Z"),
    ]
    cursor.executemany("INSERT INTO document_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", initial_docs)

    conn.commit()

    # 8. Export to Excel workbook with multiple sheets
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.read_sql_query("SELECT * FROM components", conn).to_excel(writer, sheet_name="components", index=False)
        pd.read_sql_query("SELECT * FROM suppliers", conn).to_excel(writer, sheet_name="suppliers", index=False)
        pd.read_sql_query("SELECT * FROM purchase_orders", conn).to_excel(writer, sheet_name="purchase_orders", index=False)
        pd.read_sql_query("SELECT * FROM dock_receipts", conn).to_excel(writer, sheet_name="dock_receipts", index=False)
        pd.read_sql_query("SELECT * FROM racks", conn).to_excel(writer, sheet_name="racks", index=False)
        pd.read_sql_query("SELECT * FROM document_registry", conn).to_excel(writer, sheet_name="document_registry", index=False)

    conn.close()
    print(f"BOM Generation complete: {db_path} and {excel_path} created successfully.")


if __name__ == "__main__":
    generate_bom_data()
