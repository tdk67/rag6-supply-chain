"""Verification script for Action Point 5.1: Disruption Simulation on infrastructure.db."""

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.tab_simulation import apply_disruption_scenario

def verify_sim():
    conn = sqlite3.connect("data/generated/infrastructure.db")
    cur = conn.cursor()
    b_lt = cur.execute("SELECT lead_time_weeks FROM components WHERE sku = 'SKU-GPU-MI300X'").fetchone()[0]
    print(f"Baseline Lead Time (SKU-GPU-MI300X): {b_lt} weeks")
    conn.close()

    res = apply_disruption_scenario("Scenario A: Taiwan Freight Embargo")
    print(f"Scenario Applied: {res['message']}")

    conn = sqlite3.connect("data/generated/infrastructure.db")
    cur = conn.cursor()
    m_lt = cur.execute("SELECT lead_time_weeks FROM components WHERE sku = 'SKU-GPU-MI300X'").fetchone()[0]
    print(f"Mutated Lead Time (SKU-GPU-MI300X):  {m_lt} weeks")
    conn.close()

    assert m_lt == b_lt + 16, f"Expected {b_lt+16} but got {m_lt}"
    print("[+] SUCCESS: Lead time increased by exactly +16 weeks!")

    # Reset to baseline
    apply_disruption_scenario("Baseline Normal")
    conn = sqlite3.connect("data/generated/infrastructure.db")
    cur = conn.cursor()
    r_lt = cur.execute("SELECT lead_time_weeks FROM components WHERE sku = 'SKU-GPU-MI300X'").fetchone()[0]
    print(f"Restored Lead Time (SKU-GPU-MI300X): {r_lt} weeks")
    conn.close()

if __name__ == "__main__":
    verify_sim()
