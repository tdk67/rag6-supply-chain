# Agent Roles, Personas & Retrieval Tools

## 1. Role-Based Personas (ABAC Security Model)

Aethelgard Infra-GraphRAG enforces Attribute-Based Access Control (ABAC) to ensure operational security, confidentiality, and regulatory compliance. Each persona is granted access only to relevant knowledge collections:

| Persona | Primary Focus | ChromaDB Clearance |
| :--- | :--- | :--- |
| **P1: VP of Hardware / CTO** | Hardware architecture, single points of failure, OCP compliance, software runtime (ROCm). | `technical_specs`, `compliance_docs`, `disruption_bulletins` |
| **P2: Head of Procurement** | Financial exposure, BOM unit pricing, open purchase order status, lead times. | `legal_contracts`, `disruption_bulletins`, `technical_specs` |
| **P3: General Counsel / Legal** | Contractual liability, liquidated damages, Force Majeure validity, [EU AI Act](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689) & [BSI C5](https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/Zertifizierung-nach-IT-Grundschutz/C5/c5_node.html) attestations. | `legal_contracts`, `compliance_docs`, `disruption_bulletins`, `technical_specs` |
| **P4: Lead Cloud SRE** | Thermal envelopes, cooling loop dependencies, rack redundancy, district heat PPA. | `technical_specs`, `disruption_bulletins` *(LEGAL_COMMERCIAL is restricted)* |

---

## 2. Tri-Modal Retrieval Tools

### Tool 1: Vector Search Tool (`retrieval/vector_search.py`)
- **Backing Store**: ChromaDB (Cosine similarity space).
- **Collections**:
  - `legal_contracts`: Master Service Agreements, delivery penalties, Force Majeure definitions.
  - `technical_specs`: OCP ORV3 standards, AMD MI300X guides, RoCEv2 fabric specs.
  - `compliance_docs`: [BSI C5:2024](https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/Zertifizierung-nach-IT-Grundschutz/C5/c5_node.html) attestations, [EU AI Act 2024/1689](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689) conformity statements, [NIS2 2022/2555](https://eur-lex.europa.eu/eli/dir/2022/2555/oj) policies.
  - `disruption_bulletins`: Taiwan Strait maritime advisories, Red Sea reports, BIS export updates.
- **ABAC Filter**: Automatic collection filtering based on active user persona.

### Tool 2: Graph Query Tool (`retrieval/graph_query.py`)
- **Backing Store**: NetworkX Knowledge Graph (`knowledge_graph.json`, node-link format).
- **Core Traversals**:
  - `find_single_source_components()`: Identifies components with in-degree / out-degree supplier cardinality = 1.
  - `find_taiwan_dependent_components()`: Traces multi-tier wafer and packaging foundries in Taiwan.
  - `find_cooling_failure_impact(pump_sku)`: Maps pump failure -> cooling loop -> affected racks -> district heating heat exchange.

### Tool 3: Read-Only SQL Query Tool (`retrieval/sql_query.py`)
- **Backing Store**: SQLite (`data/generated/infrastructure.db`).
- **Enforcement**: Read-only query execution (`PRAGMA query_only = ON`). DML/DDL statements are rejected.
- **Capabilities**: Exact mathematical calculations (€ order values, lead times, safety stocks, inventory discrepancy detection).

---

## 3. Reflection Loop & Response Synthesis

The agent orchestrates an Action-Inspection-Correction cycle:
1. **Pass 1 (Execution)**: Intent classification -> Tool invocation -> Tri-modal context extraction.
2. **Pass 2 (Inspection)**: Discrepancy auditing between purchase orders and dock receipts; mathematical verification of claimed totals.
3. **Pass 3 (Synthesis)**: Markdown answer generation with verified footnote citations (`[1]`, `[2]`), confidence score assessment, and Mermaid dependency diagrams.
