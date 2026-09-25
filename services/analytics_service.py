"""Analytics Service providing operational KPIs, telemetry, and discrepancy alerts.

Isolates database queries and calculations from the presentation layer (PRD §11.1).
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict
import pandas as pd

from ports.registry import AdapterRegistry
from utils.config import resolve_path, load_config


class AnalyticsService:
    """Provides operational metrics, topological statistics, and discrepancy feeds."""

    def __init__(self):
        cfg = load_config()
        self.db_path = resolve_path(cfg["paths"]["sqlite_db"])

    def get_operational_metrics(self) -> Dict[str, Any]:
        """Retrieve operational KPIs from SQLite and Knowledge Graph."""
        conn = sqlite3.connect(f"file:{self.db_path.resolve().as_posix()}?mode=ro", uri=True)
        cur = conn.cursor()

        total_components = cur.execute("SELECT COUNT(*) FROM components").fetchone()[0]
        total_val = cur.execute("SELECT SUM(total_val_eur) FROM purchase_orders").fetchone()[0] or 0.0
        total_docs = cur.execute("SELECT COUNT(*) FROM document_registry WHERE is_active = 1").fetchone()[0]
        disc_count = cur.execute("SELECT COUNT(*) FROM dock_receipts WHERE discrepancy_flag = 1").fetchone()[0]
        conn.close()

        graph_adapter = AdapterRegistry.get_graph_store()
        g_stats = graph_adapter.get_stats()

        return {
            "total_components": total_components,
            "total_val_eur": total_val,
            "total_docs": total_docs,
            "graph_nodes": g_stats["total_nodes"],
            "graph_edges": g_stats["total_edges"],
            "discrepancies": disc_count,
        }

    def get_discrepancy_feed(self, limit: int = 4) -> pd.DataFrame:
        """Fetch latest active dock discrepancy records."""
        conn = sqlite3.connect(f"file:{self.db_path.resolve().as_posix()}?mode=ro", uri=True)
        query = (
            "SELECT d.receipt_id, d.po_number, d.units_received, d.discrepancy_notes "
            "FROM dock_receipts d WHERE d.discrepancy_flag = 1 LIMIT ?"
        )
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        return df
