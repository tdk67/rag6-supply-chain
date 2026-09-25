# Implementation Plan: Aethelgard Infra-GraphRAG

Based on the Product Requirements Document (`prd.md`), this implementation plan breaks down the project into 6 phases. Each phase contains specific action points with defined dependencies, parallel execution capabilities, and mandatory verification checkpoints. 

For every action, the code generator must deliver the specified evidence before moving on to the next task.

---

## Phase 1: Data Foundation (Week 1-2)
*Objective: Set up project structure and generate the synthetic enterprise datasets (Structured, Unstructured, Graph).*

| Action Point | Description | Execution | Verification Checkpoint (Evidence to Deliver) |
| :--- | :--- | :--- | :--- |
| **1.1 Core Setup** | Create folder structure, `config.json`, `.env.example`, `requirements.txt`, and base utilities (`utils/config.py`). | **Sequential** (Do first) | **Evidence:** Run a simple Python script to load `config.json` and print the configured LLM model and API URL to stdout. |
| **1.2 BOM Generation** | Write `scripts/generate_bom.py` to create `infrastructure.db` and Excel exports with 150+ SKUs. | **Parallel** (with 1.3) | **Evidence:** Output of an SQL query showing the row counts for `components`, `purchase_orders`, and `racks` tables. |
| **1.3 Document Gen** | Write `scripts/generate_documents.py` to compile templates into PDFs/TXTs in `data/documents/`. | **Parallel** (with 1.2) | **Evidence:** A terminal `ls` (or directory tree) of `data/documents/` showing the generated MSA and Spec files. |
| **1.4 Graph Seeding** | Write `scripts/seed_graph.py` to extract relationships from `infrastructure.db` into a NetworkX graph. | **Sequential** (Needs 1.2) | **Evidence:** Console output from `scripts/validate_data.py` proving node/edge counts match targets (~500 nodes, 1500 edges) without integrity errors. |

---

## Phase 2: Document Ingestion Pipeline (Week 2-3)
*Objective: Build the ingestion system to parse, chunk, and embed documents into ChromaDB, while tracking lifecycles.*

| Action Point | Description | Execution | Verification Checkpoint (Evidence to Deliver) |
| :--- | :--- | :--- | :--- |
| **2.1 Parser & Extractor** | Implement `ingestion/parser.py` (PyMuPDF) to extract text and basic metadata from PDF/TXT files. | **Parallel** (with 2.4) | **Evidence:** Run a test script on `Supermicro_GPU_Nodes_MSA.pdf` printing the extracted text of page 1 and its metadata. |
| **2.2 Format-Aware Chunker** | Implement `ingestion/chunker.py` using format-aware splitting (Section-aware for legal, Heading-based for tech specs). | **Sequential** (Needs 2.1) | **Evidence:** Output showing 3 sample chunks from a legal PDF, explicitly displaying the `section_heading` in their metadata. |
| **2.3 Vector Indexing** | Implement `ingestion/embedder.py` using ChromaDB and local `BAAI/bge-small-en-v1.5` embeddings. | **Sequential** (Needs 2.2) | **Evidence:** A script that queries ChromaDB for "Liquidated damages" and returns the top 1 matching chunk ID and similarity score. |
| **2.4 Lifecycle Registry** | Implement `ingestion/lifecycle.py` to handle document hashing, registration, and version deprecation. | **Parallel** (with 2.1) | **Evidence:** SQLite dump of the document registry showing an `ACTIVE` version and a `DEPRECATED` version of a document. |

---

## Phase 3: Tri-Modal Retrieval & Tools (Week 3-4)
*Objective: Develop the three core tools that the AI agent will use to fetch context (Vector, Graph, SQL).*

| Action Point | Description | Execution | Verification Checkpoint (Evidence to Deliver) |
| :--- | :--- | :--- | :--- |
| **3.1 SQL Tool** | Implement `retrieval/sql_query.py` combining text-to-SQL logic and parameterized fallback queries (Read-Only). | **Parallel** (with 3.2, 3.3) | **Evidence:** Run the tool with "What is the total value of PO-8821?" and output the resulting DataFrame/JSON response. |
| **3.2 Graph Tool** | Implement `retrieval/graph_query.py` combining Text-to-Cypher generation and pre-defined traversal templates. | **Parallel** (with 3.1, 3.3) | **Evidence:** Run the tool with "Which supplier provides SKU-GPU-MI300X?" and output the returning NetworkX node metadata. |
| **3.3 Vector Tool** | Implement `retrieval/vector_search.py` wrapping ChromaDB queries with ABAC/Persona metadata filters. | **Parallel** (with 3.1, 3.2) | **Evidence:** Retrieve chunks for "Force Majeure" under the 'Legal' persona, then demonstrate failure/filtering under the 'SRE' persona. |

---

## Phase 4: Agent Core & Reasoning Engine (Week 4-5)
*Objective: Wire the tools into a multi-step reflection loop with prompt injection safety and hallucination checks.*

| Action Point | Description | Execution | Verification Checkpoint (Evidence to Deliver) |
| :--- | :--- | :--- | :--- |
| **4.1 Safety Guardrails** | Implement `agent/guardrails.py` for pre-retrieval (injection) and post-retrieval (grounding) checks. | **Parallel** (with 4.2) | **Evidence:** Output log showing a query like "Ignore instructions" being caught and blocked with a warning message. |
| **4.2 Intent Router** | Implement `agent/intent_router.py` to classify queries into one of the 6 GraphRAG patterns. | **Parallel** (with 4.1) | **Evidence:** A script that passes Benchmark Q1 through the router and asserts the output is exactly "P3: Sequential Graph-First". |
| **4.3 Reflection Loop** | Implement `agent/orchestrator.py` & `response_builder.py` to handle action-inspection-correction loops. | **Sequential** (Needs 4.1, 4.2) | **Evidence:** Full execution trace (Glass Box log) of Benchmark Q3 showing intent classification, tool invocation, and the structured JSON output with citations. |

---

## Phase 5: Streamlit UI & Dashboard (Week 5-6)
*Objective: Build the executive dashboard integrating chat, data simulation, and knowledge base analytics.*

| Action Point | Description | Execution | Verification Checkpoint (Evidence to Deliver) |
| :--- | :--- | :--- | :--- |
| **5.1 Tab 2 (Simulation)** | Build `ui/tab_simulation.py` to toggle disruptions (Taiwan embargo, Insolvency). | **Parallel** (with 5.2, 5.3) | **Evidence:** A screenshot or terminal output confirming the UI can trigger a change in `infrastructure.db` lead times. |
| **5.2 Tab 3 (Analytics)** | Build `ui/tab_analytics.py` using Mermaid/pyvis for graph visualization and metrics tiles. | **Parallel** (with 5.1, 5.3) | **Evidence:** Console output verifying that `st.metric` and `pyvis` network generation functions execute without errors. |
| **5.3 Tab 4 (Ingestion)** | Build `ui/tab_ingestion.py` allowing drag-and-drop file upload to ChromaDB and registry. | **Parallel** (with 5.1, 5.2) | **Evidence:** Output log showing a new file uploaded via Streamlit, parsed, and indexed into ChromaDB successfully. |
| **5.4 Tab 1 (AI Console)** | Build `ui/tab_decision_console.py` linking the Agent Orchestrator to the chat UI and Benchmark Carousel. | **Sequential** (Needs 4.3) | **Evidence:** A complete Streamlit run output indicating no render errors, and a log showing async query execution streaming intermediate states to the UI. |
| **5.5 Main App Shell** | Assemble `app.py` to import and render all tabs with a consistent persona selector header. | **Sequential** (Needs 5.1-5.4) | **Evidence:** Execution of `streamlit run app.py` launches the server cleanly without errors. |

---

## Phase 6: Testing & Deliverables (Week 6-7)
*Objective: Guarantee system stability, measure RAG metrics, and finalize documentation.*

| Action Point | Description | Execution | Verification Checkpoint (Evidence to Deliver) |
| :--- | :--- | :--- | :--- |
| **6.1 Unit & Int. Tests** | Write `pytest` test suites in `tests/unit/` and `tests/integration/`. | **Parallel** (with 6.2) | **Evidence:** `pytest` CLI output displaying `100% passing` and a coverage report proving `> 80%` test coverage. |
| **6.2 RAG Evaluation** | Build and run `scripts/evaluate_rag.py` against the 10 benchmark queries using RAGAS or custom judge. | **Parallel** (with 6.1) | **Evidence:** Output JSON or terminal summary showing Faithfulness and Answer Correctness > 0.85 across the 10 benchmarks. |
| **6.3 Documentation** | Complete `README.md`, `docs/architecture.md`, `docs/agent_roles.md`, and `docs/limitations.md`. | **Sequential** (Final step) | **Evidence:** File listings of `docs/` and a snippet of `README.md` verifying documentation completeness. |
