# Capstone Project: RAG Architecture & Business Case Exploration

This document summarizes five high-impact enterprise business cases tailored for an **Agentic GraphRAG** decision support system that integrates:
- **Unstructured Documents (PDF/TXT)** via Vector DB
- **Tabular & Operational Data (CSV/Excel)** via Structured DB / GraphQL queries
- **Multi-hop Relational Entities** via Graph DB (Knowledge Graph / Cypher)
- **Agentic Routing** across the 6 advanced GraphRAG architectural patterns (Text-to-Cypher, Parallel Hybrid, Sequential Graph-First, Sequential Vector-First, Adaptive Router, and Multi-Step Agentic Loops).

---

## 1. Enterprise Supply Chain Resilience & Multi-Tier Disruption Risk

- **Domain**: Global Manufacturing, High-Tech Procurement & Sovereign AI Infrastructure.
- **Problem Statement**: Supply chain disruptions (geopolitical embargoes, factory outages, natural disasters, port strikes, vendor insolvencies) cascade through multi-tier sub-assemblies. Traditional search cannot calculate financial impact or traverse BOM (Bill of Materials) dependency graphs.
- **Data Landscape**:
  - **PDF/TXT**: Master Service Agreements (MSAs), Force Majeure clauses, Supplier audit reports, Compliance certifications, Geopolitical risk bulletins.
  - **Excel / Structured DB**: Component Bill of Materials (BOM), unit costs, lead times, stock on hand, delivery schedules, minimum order quantities (MOQs).
  - **Graph DB**: Multi-tier dependency network (`Product -> Assembly -> Sub-component -> Tier-1/2/3 Supplier -> Fabrication Plant -> Geographic Region`).
  - **GraphQL / DB API**: Real-time SKU stock levels, open purchase orders, supplier reliability scores.
- **RAG Variant Utilization**:
  - *Pattern 1 (Text-to-Cypher)*: Trace direct and indirect supplier dependency paths.
  - *Pattern 3 (Sequential Graph-First)*: Filter affected components in the graph, then query Excel/DB for cost and inventory exposure.
  - *Pattern 2 (Parallel Hybrid)*: Retrieve legal liability clauses while concurrently summing inventory loss.
- **Evaluation**:
  - **Fit for Requirements**: 9.9 / 10
  - **Uniqueness**: 9.3 / 10
  - **Real-World Problem**: 9.9 / 10

---

## 2. Clinical Trials Intelligence & Drug Safety Pharmacovigilance

- **Domain**: Biopharma, Clinical Research Organizations (CRO), Regulatory Affairs.
- **Problem Statement**: Cross-referencing experimental protocols, biological targets, cohort inclusion criteria, and adverse event severity logs across hundreds of clinical trials.
- **Data Landscape**:
  - **PDF/TXT**: Clinical trial protocol PDFs (study designs, inclusion/exclusion criteria, amendments), FDA advisory briefings, medical papers.
  - **Excel / Structured DB**: Patient cohort demographic tables, lab biomarker values, adverse event logs with numerical severity grading.
  - **Graph DB**: Biomedical Knowledge Graph (`Drug -> Molecular Target -> Disease/Indication -> Biological Pathway -> Adverse Effect -> Sponsor`).
  - **GraphQL / DB API**: ClinicalTrials.gov schema queries (NCT IDs, recruitment status, completion dates, trial phases).
- **RAG Variant Utilization**:
  - *Pattern 5 (Adaptive Router)*: Directs biological mechanism queries to Graph, numerical enrollment stats to GraphQL/DB, and narrative physician notes to Vector DB.
  - *Pattern 6 (Agentic GraphRAG)*: Multi-step investigation hopping between anomalous biomarkers, molecular pathways, and protocol revisions.
- **Evaluation**:
  - **Fit for Requirements**: 9.8 / 10
  - **Uniqueness**: 9.6 / 10
  - **Real-World Problem**: 9.8 / 10

---

## 3. Corporate M&A Due Diligence & Ultimate Beneficial Ownership (UBO)

- **Domain**: Private Equity, Investment Banking, Legal Compliance & Anti-Money Laundering (AML).
- **Problem Statement**: Due diligence teams must inspect labyrinthine corporate ownership structures, regulatory sanctions lists, and complex debt/financial models across thousands of virtual data room documents.
- **Data Landscape**:
  - **PDF/TXT**: Confidential Information Memorandums (CIMs), Merger agreements, Credit facility contracts, Board minutes, Regulatory filings.
  - **Excel / Structured DB**: Cap tables (equity percentages), 5-year financial models (EBITDA, DCF projections, debt schedules), employee compensation sheets.
  - **Graph DB**: Entity Ownership Graph (`Ultimate Holding Company -> Parent -> Offshore Sub -> Joint Venture -> Shareholders / PEPs`).
  - **GraphQL / DB API**: Corporate register queries, verified balance sheet summaries, registered agent details.
- **RAG Variant Utilization**:
  - *Pattern 1 (Text-to-Cypher)*: Traverse offshore holding shells to determine ultimate beneficial ownership percentage.
  - *Pattern 4 (Sequential Vector-First)*: Locate indemnity and governing law clauses in contracts, then verify corresponding financial liabilities in Excel models.
- **Evaluation**:
  - **Fit for Requirements**: 9.6 / 10
  - **Uniqueness**: 9.1 / 10
  - **Real-World Problem**: 9.7 / 10

---

## 4. DevSecOps Blast Radius & Cyber Incident Response

- **Domain**: Enterprise Cloud Security, Incident Response, SecOps.
- **Problem Statement**: When a zero-day exploit or cloud credential compromise occurs, security responders must determine which microservices are vulnerable, trace network/identity blast radiuses, and retrieve mitigation playbooks under extreme time pressure.
- **Data Landscape**:
  - **PDF/TXT**: Postmortem incident reports, vendor SOC2 / ISO compliance audit reports, MITRE ATT&CK threat intelligence notes, CVE disclosures.
  - **Excel / Structured DB**: CMDB asset inventories, vulnerability scan tables (CVSS scores, CVE IDs, patch status), server IP / port mappings.
  - **Graph DB**: Cloud Infrastructure Graph (`Public Ingress -> Load Balancer -> Service/Pod -> IAM Role -> Secret/Key -> Database/Bucket`).
  - **GraphQL / DB API**: Cloud asset query API (running container tags, security group rules, patch levels).
- **RAG Variant Utilization**:
  - *Pattern 3 (Sequential Graph-First)*: Map traversal from compromised host to crown-jewel assets, then query Excel/DB for unpatched versions.
  - *Pattern 2 (Parallel Hybrid)*: Query vulnerability scores alongside compliance incident playbooks.
- **Evaluation**:
  - **Fit for Requirements**: 9.7 / 10
  - **Uniqueness**: 9.0 / 10
  - **Real-World Problem**: 9.9 / 10

---

## 5. Aviation / Heavy Machinery Predictive Maintenance & Root Cause Analysis

- **Domain**: Aerospace, Industrial IoT, Heavy Equipment Fleet Operations.
- **Problem Statement**: Diagnosing anomalous telemetry across a fleet of complex machinery requires linking mechanical assembly breakdowns, vendor parts manufacturing batches, and thousands of pages of maintenance manuals.
- **Data Landscape**:
  - **PDF/TXT**: Aircraft Flight Operations Manuals (AFM), Technical Service Bulletins (OEM engineering advisories), Field technician log notes.
  - **Excel / Structured DB**: Sensor telemetry aggregate logs, component flight hours/operating cycles, replacement inventory stock, repair costs.
  - **Graph DB**: Mechanical Assembly Hierarchy (`Aircraft -> Engine -> High-Pressure Turbine -> Compressor Blade -> Foundry Batch -> Maintenance Station`).
  - **GraphQL / DB API**: Fleet status API, open maintenance work orders, part delivery tracking.
- **RAG Variant Utilization**:
  - *Pattern 1 (Text-to-Cypher)*: Trace all aircraft in service that contain parts from a specific suspect supplier metallurgical batch.
  - *Pattern 6 (Agentic GraphRAG)*: Synthesize sensor vibration trends with manufacturer service bulletins and repair manuals.
- **Evaluation**:
  - **Fit for Requirements**: 9.5 / 10
  - **Uniqueness**: 9.4 / 10
  - **Real-World Problem**: 9.6 / 10

---

## Selection for Deep Dive: Idea 1 (Specialized for Sovereign AI Cloud Data Center)

**Idea 1** has been chosen for detailed formulation in [idea01.md](idea01.md). It will be framed around a **European Sovereign AI Cloud Startup** planning, deploying, and operating an independent AI data center without single-source dependency on US/China hardware or software.
