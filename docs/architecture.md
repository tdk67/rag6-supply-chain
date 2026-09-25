# System Architecture: Aethelgard Infra-GraphRAG

## 1. Executive Architecture Overview

Aethelgard Infra-GraphRAG is an autonomous, tri-modal Agentic GraphRAG system designed for sovereign European AI data center operators. It unites physical hardware topologies (Graph DB), rigid inventory calculations (SQLite SSOT), and unstructured legal contracts (Vector DB) across six adaptive reasoning patterns.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       STREAMLIT SHOWCASE UI & DECISION CONSOLE              │
│       - AI Decision Console   - Simulation Studio   - Analytics Dashboard   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Async Query / Progress Events)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    AGENT ORCHESTRATOR & REASONING ENGINE                    │
│  ┌────────────────────────┐  ┌───────────────────────┐  ┌─────────────────┐ │
│  │ Safety Guardrails      │  │ Adaptive Intent Router│  │ Reflection Loop │ │
│  │ (Pre/Post Verification)│  │ (6 GraphRAG Patterns) │  │ (Action-Inspect)│ │
│  └────────────────────────┘  └───────────────────────┘  └─────────────────┘ │
└──────────────┬───────────────────────┬───────────────────────┬──────────────┘
               │                       │                       │
     ┌─────────▼─────────┐   ┌─────────▼─────────┐   ┌─────────▼─────────┐
     │ Tool 1: Vector    │   │ Tool 2: Graph     │   │ Tool 3: SQL       │
     │ Search Tool       │   │ Query Tool        │   │ Query Tool        │
     │ (ChromaDB + ABAC) │   │ (NetworkX Traver.)│   │ (SQLite Read-Only)│
     └─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘
               │                       │                       │
┌──────────────▼───────────────────────▼───────────────────────▼──────────────┐
│                            HEXAGONAL DATA LAYER                             │
│  ┌────────────────────────┐  ┌───────────────────────┐  ┌─────────────────┐ │
│  │ ChromaDB Vector Store  │  │ NetworkX Graph Store  │  │ SQLite Database │ │
│  │ (14 Sovereign Contracts│  │ (332 Nodes, 1296 Edges│  │ (SSOT BOM, POs, │ │
│  │  in 5 typed collections│  │  physical & supplier) │  │  Dock Receipts) │ │
│  └────────────────────────┘  └───────────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Tri-Modal Knowledge Substrate

Enterprise data center operations cannot be solved with pure vector search or pure relational databases alone:
1. **Unstructured Data (ChromaDB)**: Encapsulates Master Service Agreements (MSAs), Technical Specifications (OCP ORV3, ROCm deployment guides), Municipal Waste Heat PPAs, and Geopolitical Risk Bulletins.
2. **Relational Data (SQLite SSOT)**: Serves as the authoritative single source of truth (SSOT) for BOM items, unit costs in EUR, lead times in weeks, purchase orders, and loading dock delivery manifests.
3. **Graph Topology (NetworkX / Neo4j)**: Encodes multi-tier hardware hierarchy `(Facility)->(Rack)->(Chassis)->(Component)`, supplier relationships `(Component)-[:SUPPLIED_BY]->(Supplier)-[:SUBCONTRACTS_TO]->(SubTier)`, and cooling dependencies `(Loop)-[:DEPENDS_ON_PUMP]->(Component)`.

---

## 3. CQRS Pattern & Trap Mitigation

- **Command Query Responsibility Segregation (CQRS)**: SQLite acts as the transactional Command store. When disruptions are simulated in the Simulation Studio, SQLite tables are mutated first. The Knowledge Graph is deterministically compiled as a read-projection from SQLite, avoiding distributed lock deadlocks.
- **Trap 2 Mitigation (Data Rot & Discrepancies)**: The system does not trust purchase orders blindly. It performs automated triangulation between purchase order commitments and physical dock delivery receipts (`dock_receipts`), explicitly surfacing discrepancies.
- **Trap 3 Mitigation (Architectural Sync)**: Read projections are cached and reproducible via seeded deterministic generators (`scripts/generate_bom.py`, `scripts/seed_graph.py`).

---

## 4. The 6 GraphRAG Architectural Patterns

Based on Sarkar (2026), the Adaptive Intent Router classifies queries into:
- **P1: Deterministic Text-to-Cypher**: Pure graph topology audits (single-source dependencies, multi-hop relationship checks).
- **P2: Parallel Hybrid**: Questions combining legal clauses with financial calculations or topology (Force Majeure + PO penalties).
- **P3: Sequential Graph-First**: Blast radius cascades where affected nodes are discovered first in the graph, followed by SQL impact calculation.
- **P4: Sequential Table-First**: Quantitative comparisons that filter inventory data first, then evaluate software compatibility.
- **P5: Adaptive Router (Vector-Primary)**: Regulatory and compliance whitepapers ([EU AI Act 2024/1689](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689), [BSI C5:2024](https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/Zertifizierung-nach-IT-Grundschutz/C5/c5_node.html) attestations).
- **P6: Agentic Multi-Step Loop**: Complex crisis scenarios requiring iterative multi-turn reflection across all three modalities.
