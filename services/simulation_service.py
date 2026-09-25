"""Simulation Service applying scenario mutations and CQRS graph re-projections.

Isolates database state mutations from the presentation layer (PRD §11.1).
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict
import pandas as pd
from utils.config import resolve_path, load_config
from scripts.seed_graph import build_knowledge_graph
from scripts.generate_bom import generate_bom_data


class SimulationService:
    """Manages disruption injection, CQRS synchronization, and SSOT previews."""

    def __init__(self):
        cfg = load_config()
        self.db_path = resolve_path(cfg["paths"]["sqlite_db"])

    def apply_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Apply deterministic disruption mutations to SQLite SSOT and compile graph."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        if scenario_name == "Scenario A: Taiwan Freight Embargo":
            # Add 16 weeks to lead time for all Taiwan-origin components
            cur.execute(
                """
                UPDATE components
                SET lead_time_weeks = lead_time_weeks + 16
                WHERE country_of_origin = 'Taiwan' OR tier2_manufacturer LIKE '%Taiwan%' OR tier2_manufacturer LIKE '%TSMC%'
                """
            )
            affected_comps = cur.rowcount
            conn.commit()
            conn.close()

            # Recompile graph projection (CQRS)
            build_knowledge_graph()
            return {
                "scenario": scenario_name,
                "affected_components": affected_comps,
                "status": "MUTATED",
                "message": f"Applied +16 weeks lead time penalty to {affected_comps} Taiwan-dependent components.",
            }

        elif scenario_name == "Scenario B: Submer Manifold Insolvency":
            # Mark Submer as IN_RESTRUCTURING and freeze purchase orders
            cur.execute("UPDATE suppliers SET status = 'IN_RESTRUCTURING' WHERE name LIKE '%Submer%'")
            cur.execute("UPDATE purchase_orders SET status = 'DELAYED' WHERE supplier_id = 'SUP-004'")
            conn.commit()
            conn.close()

            build_knowledge_graph()
            return {
                "scenario": scenario_name,
                "status": "MUTATED",
                "message": "Submer marked as IN_RESTRUCTURING. Purchase orders frozen.",
            }

        else:  # Baseline Normal
            cur.execute("UPDATE suppliers SET status = 'ACTIVE' WHERE status = 'IN_RESTRUCTURING'")
            cur.execute("UPDATE purchase_orders SET status = 'OPEN' WHERE status = 'DELAYED'")
            conn.commit()
            conn.close()

            build_knowledge_graph()
            return {
                "scenario": "Baseline (No Disruptions)",
                "status": "RESET",
                "message": "All supplier and purchase order statuses reset to baseline.",
            }

    def regenerate_master_baseline(self) -> Dict[str, Any]:
        """Regenerate complete synthetic BOM dataset and rebuild knowledge graph."""
        generate_bom_data()
        build_knowledge_graph()
        return {"status": "SUCCESS", "message": "BOM and Knowledge Graph regenerated successfully."}

    def get_components_preview(self, limit: int = 15) -> pd.DataFrame:
        """Fetch preview of hardware components."""
        conn = sqlite3.connect(f"file:{self.db_path.resolve().as_posix()}?mode=ro", uri=True)
        query = (
            "SELECT sku, part_name, category, country_of_origin, unit_cost_eur, lead_time_weeks, current_stock "
            "FROM components LIMIT ?"
        )
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        return df

    def get_purchase_orders_preview(self, limit: int = 15) -> pd.DataFrame:
        """Fetch preview of purchase orders."""
        conn = sqlite3.connect(f"file:{self.db_path.resolve().as_posix()}?mode=ro", uri=True)
        query = (
            "SELECT po_number, sku, supplier_id, status, quantity, total_val_eur, agreed_delivery_date "
            "FROM purchase_orders LIMIT ?"
        )
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        return df

    def get_dock_discrepancies_preview(self, limit: int = 15) -> pd.DataFrame:
        """Fetch preview of loading dock delivery discrepancies."""
        conn = sqlite3.connect(f"file:{self.db_path.resolve().as_posix()}?mode=ro", uri=True)
        query = (
            "SELECT d.receipt_id, d.po_number, po.quantity AS ordered_qty, d.units_received, d.discrepancy_notes "
            "FROM dock_receipts d JOIN purchase_orders po ON d.po_number = po.po_number "
            "WHERE d.discrepancy_flag = 1 LIMIT ?"
        )
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        return df
