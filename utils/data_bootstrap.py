"""First-run data provisioning for serverless / ephemeral deployments.

On Streamlit Cloud (and other serverless hosts), the data/ directory is not
shipped with the repo, so SQLite SSOT, knowledge graph files, and the ChromaDB
persistent index do not exist on first boot.

This module centralizes:
  - a readiness check (is the dataset fully provisioned?),
  - an idempotent generate_all_data() that builds SQLite, documents, the
    NetworkX knowledge graph, and the Chroma vector index.

It is intentionally side-effect free at import time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from utils.config import load_config, resolve_path

# Store names used by ChromaDBAdapter.COLLECTIONS
# (chart below just documents what a "provisioned" dataset looks like)
REQUIRED_COLLECTIONS = [
    "legal_contracts",
    "technical_specs",
    "compliance_docs",
    "disruption_bulletins",
    "table_summaries",
]

_LAST_CHECK: Dict[str, object] = {}


def dataset_status() -> Dict:
    """Return a dict describing whether the local dataset is provisioned.

    Checks (in order):
      - SQLite SSOT database exists and is non-empty,
      - knowledge graph node-link JSON exists and parses,
      - ChromaDB persistent store has at least one non-empty collection.

    No exceptions are raised for a missing dataset; callers use the flags.
    """
    cfg = load_config()
    db_path = resolve_path(cfg["paths"]["sqlite_db"])
    graph_path = resolve_path(cfg["paths"]["graph_file"])
    if graph_path.suffix == ".json":
        graph_json = graph_path
    else:
        graph_json = graph_path.with_suffix(".json")
    chroma_dir = resolve_path(cfg["paths"]["chroma_dir"])

    sqlite_ok = db_path.exists() and db_path.stat().st_size > 0
    try:
        import sqlite3

        if sqlite_ok:
            conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
            try:
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM components")
                sqlite_ok = (cur.fetchone()[0] or 0) > 0
            finally:
                conn.close()
    except Exception:
        sqlite_ok = False

    graph_ok = False
    if graph_json.exists() and graph_json.stat().st_size > 0:
        try:
            import json

            data = json.loads(graph_json.read_text(encoding="utf-8"))
            graph_ok = bool(data) and "nodes" in data and len(data["nodes"]) > 0
        except Exception:
            graph_ok = False

    vector_ok = False
    if chroma_dir.exists():
        try:
            from ports.registry import AdapterRegistry

            stats = AdapterRegistry.get_vector_store().get_collection_stats()
            vector_ok = any((stats.get(name, 0) or 0) > 0 for name in REQUIRED_COLLECTIONS)
        except Exception:
            vector_ok = False

    return {
        "sqlite_ok": sqlite_ok,
        "graph_ok": graph_ok,
        "vector_ok": vector_ok,
        "provisioned": sqlite_ok and graph_ok and vector_ok,
    }


def generate_all_data(progress_cb=None) -> None:
    """Generate (or regenerate) the full synthetic dataset.

    Order matters:
      1. BOM / SQLite SSOT + Excel export        (scripts.generate_bom)
      2. Synthetic PDF/TXT documents             (scripts.generate_documents)
      3. Knowledge graph compiled from SQLite    (scripts.seed_graph)
      4. ChromaDB vector index over documents    (ingestion.embedder.index_all)

    Idempotent: safe to call repeatedly (regenerates data in place).
    """
    from scripts.generate_bom import generate_bom_data
    from scripts.generate_documents import generate_all_documents
    from scripts.seed_graph import build_knowledge_graph

    def _report(stage: str):
        if progress_cb:
            progress_cb(stage)

    _report("Generating Bill of Materials & SQLite SSOT...")
    generate_bom_data()

    _report("Generating synthetic contracts & technical documents (PDF/TXT)...")
    generate_all_documents()

    _report("Compiling knowledge graph from SSOT...")
    build_knowledge_graph()

    _report("Embedding documents into ChromaDB...")
    from ingestion.embedder import index_all

    index_all()

    _report("Dataset provisioning complete.")


def missing_summary(status: Dict) -> str:
    """Human readable list of what components are missing."""
    missing = []
    if not status.get("sqlite_ok"):
        missing.append("SQLite SSOT database")
    if not status.get("graph_ok"):
        missing.append("knowledge graph")
    if not status.get("vector_ok"):
        missing.append("Chroma vector index")
    return "None" if not missing else ", ".join(missing)