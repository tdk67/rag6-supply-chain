# Aethelgard Infra-GraphRAG
**A Tri-Modal Sovereign Infrastructure & Supply Chain Intelligence Engine**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Architecture: Tri-Modal](https://img.shields.io/badge/Architecture-Tri--Modal%20GraphRAG-purple.svg)](#architecture)
[![Testing: Pytest](https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen.svg)](#testing)

---

## 1. Executive Summary

Sovereign AI data center operators are frequently paralyzed by fragmented information silos between multi-tier hardware dependency graphs, complex legal supplier contracts, and volatile inventory spreadsheets. When global supply chain shocks hit (e.g. maritime route blocks, export restrictions, supplier restructuring), evaluating the operational, legal, and financial blast radius can take weeks.

**Aethelgard Infra-GraphRAG** solves this crisis through an autonomous, tri-modal Agentic GraphRAG system that unites:
1. **Physical Hardware Topologies & Multi-Tier Networks** (NetworkX Knowledge Graph)
2. **Contractual SLAs, MSAs & Sovereignty Standards** (ChromaDB Vector Store)
3. **Master BOM Inventories, POs & Dock Manifests** (SQLite SSOT Database)

The agent operates across **six adaptive GraphRAG architectural patterns** (Sarkar, 2026), with automated prompt injection guardrails, a multi-step reflection loop, and zero-hallucination footnote citations.

---

## 2. Key Capabilities & Features

- **Tri-Modal Context Synthesis**: Concurrently queries relational SQL, graph topology traversals, and semantic vector collections.
- **Adaptive 6-Pattern Intent Router**: Automatically selects from 6 GraphRAG patterns:
  - `P1`: Deterministic Text-to-Cypher (Single-source supplier audit)
  - `P2`: Parallel Hybrid (Force Majeure + PO delay penalties)
  - `P3`: Sequential Graph-First (Taiwan freight disruption cascade)
  - `P4`: Sequential Table-First (Hardware cost and bandwidth comparison)
  - `P5`: Adaptive Router / Vector-Primary (EU AI Act & BSI C5 attestations)
  - `P6`: Agentic Multi-Step Loop (Crisis response & spare parts runway)
- **Role-Based Security & ABAC Clearance**: Four persona viewpoints with strict access control:
  - `CTO / Hardware Architecture`
  - `Head of Procurement`
  - `General Counsel / Compliance`
  - `Lead Cloud SRE` *(Strictly blocked from sensitive legal clauses)*
- **Data Discrepancy Auditing (Trap 2 Mitigation)**: Triangulates ERP purchase order quantities with loading dock delivery receipts (`dock_receipts`), explicitly surfacing backorders and delivery deficits.
- **Deterministic Disruption Simulator**: 1-click scenario simulator (e.g., Taiwan embargo, vendor restructuring) that mutates the SSOT and re-projects the graph dynamically under CQRS.

---

## 3. Quick Start & Installation

### Prerequisites
- Python 3.11+
- Virtual environment tool (`venv` or `uv`)

### 1. Setup & Environment
```bash
# Navigate to the project root directory
cd <project-directory>

# Install dependencies
pip install -r requirements.txt

# Configure secrets (copy template)
cp .env.example .env
# Edit .env and insert OPENROUTER_API_KEY (optional: offline deterministic mode works automatically)
```

### 2. Generate Synthetic Datasets
```bash
# Generate BOM, Purchase Orders, and Dock Receipts (SQLite + Excel)
python scripts/generate_bom.py

# Compile synthetic PDFs and engineering specifications
python scripts/generate_documents.py

# Seed the NetworkX Knowledge Graph from SQLite SSOT
python scripts/seed_graph.py

# Index documents into ChromaDB collections
python ingestion/embedder.py

# Verify 100% referential data integrity
python scripts/validate_data.py
```

### 3. Launch Streamlit Showcase UI
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 4. Acceptance Benchmarks & Testing

Run the full automated test suite with coverage:
```bash
python -m pytest tests/ --cov=agent --cov=retrieval --cov=ingestion --cov=utils --cov-report=term-missing
```

Run the 10 Benchmark RAG evaluation suite:
```bash
python scripts/evaluate_rag.py
```

---

## 5. Repository Structure

```
├── app.py                         # Clean Streamlit shell entry point (< 150 lines)
├── config.json                    # All operational settings & model parameters
├── .env.example                   # Secret template (clean code architecture)
├── requirements.txt               # Pinned dependencies
├── ui/                            # Streamlit Presentation Layer (4 Tabs)
│   ├── tab_decision_console.py    # Tab 1: AI Chat & 1-Click Benchmark Carousel
│   ├── tab_simulation.py          # Tab 2: Disruption Simulator & Data Studio
│   ├── tab_analytics.py           # Tab 3: PyVis Graph & Metrics Dashboard
│   └── tab_ingestion.py           # Tab 4: File Ingestion & Document Lifecycle
├── agent/                         # Agent Reasoning Core
│   ├── orchestrator.py            # Reflection loop (Action-Inspect-Correct)
│   ├── intent_router.py           # 6-pattern classification router
│   ├── guardrails.py              # Pre/post retrieval safety & grounding checks
│   └── response_builder.py        # Confidence calculation & citation assembly
├── retrieval/                     # Tri-Modal Retrieval Tools
│   ├── vector_search.py           # ChromaDB search with ABAC filters
│   ├── graph_query.py             # NetworkX topology traversals
│   └── sql_query.py               # Read-only SQLite query tool
├── ingestion/                     # Ingestion & Lifecycle Pipeline
│   ├── parser.py                  # PyMuPDF text & metadata extraction
│   ├── chunker.py                 # Format-aware section chunking
│   ├── embedder.py                # ChromaDB vector indexing
│   └── lifecycle.py               # Document hashing & version deprecation
├── ports/                         # Hexagonal Port Interfaces & Adapters
│   ├── base.py                    # VectorStorePort, GraphStorePort, LLMProviderPort
│   ├── vector_store/              # ChromaDBAdapter
│   ├── graph_store/               # NetworkXAdapter
│   ├── llm_provider/              # OpenRouterAdapter
│   └── registry.py                # Dependency injection container
├── scripts/                       # Data Generation & Benchmark Runners
│   ├── generate_bom.py            # SQLite & Excel BOM generator
│   ├── generate_documents.py      # Synthetic PDF compiler
│   ├── seed_graph.py              # Graph compiler from SQLite
│   ├── validate_data.py           # Referential integrity validator
│   └── evaluate_rag.py            # 10 Benchmark evaluation runner
├── templates/                     # Standalone HTML templates for PDFs
├── docs/                          # Architectural & Design Documentation
│   ├── architecture.md            # Tri-Modal CQRS system architecture
│   ├── agent_roles.md             # Personas, ABAC clearance & tools
│   └── limitations.md             # Prototype constraints & scaling roadmap
└── tests/                         # Unit and integration test suite (pytest)
```

---

## 6. License & Sovereignty Compliance

Engineered in full compliance with:
- **[Regulation (EU) 2024/1689 (EU AI Act)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689)** — European Parliament and Council regulation establishing harmonised rules on artificial intelligence.
- **[German BSI Cloud Computing Compliance Criteria Catalogue (C5:2024)](https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/Zertifizierung-nach-IT-Grundschutz/C5/c5_node.html)** — German Federal Office for Information Security criteria for secure and sovereign cloud computing.
- **[Directive (EU) 2022/2555 (NIS2 Directive)](https://eur-lex.europa.eu/eli/dir/2022/2555/oj)** — Measures for a high common level of cybersecurity and critical infrastructure supply chain security across the European Union.

---

## 7. Docker Deployment

A production-ready Docker setup is included:

```bash
# Build & start (regenerates synthetic data inside the container)
docker compose -f docker-compose.deploy.yml up -d --build

# App is served at http://localhost:8510
# Set OPENROUTER_API_KEY to enable live LLM reasoning
# (without a key, the offline deterministic fallback mode is used)
```

- **Dockerfile** — multi-stage Python 3.11-slim image; generates BOM/documents/graph/Chroma
  index at build time so the container is self-contained (no API key required for the demo).
- **Ports** — binds `127.0.0.1:8510` → container `8501`; reverse-proxied by nginx at
  `https://supply-chain.taskmind-ai.com`.
