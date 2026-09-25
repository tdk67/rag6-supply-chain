# System Limitations & Future Roadmap

## 1. Prototype Scope & Known Limitations

### 1.1 In-Process Vector Storage (ChromaDB)
- **Current State**: Uses embedded ChromaDB with in-memory SQLite and local HNSW index segments.
- **Production Path**: Transition to clustered distributed vector databases such as **Qdrant** or **Milvus** with dedicated shard management and raft consensus for high-throughput multi-tenant deployments.

### 1.2 Knowledge Graph Scaling (NetworkX to Neo4j)
- **Current State**: NetworkX operates in-memory (`knowledge_graph.gpickle`). While ideal for 500 nodes and instant graph traversal in demonstrations, it does not support ACID transactions across multiple writers.
- **Production Path**: Migrate to clustered **Neo4j** or **Memgraph** utilizing the pre-built `ports/graph_store/neo4j_adapter.py` interface with Cypher query optimization.

### 1.3 Synthetic Grounding Data vs. Live CMDB
- **Current State**: Grounded in 155 synthetic OCP-compliant SKUs and 14 synthesized legal/regulatory PDFs.
- **Production Path**: Integrate with live enterprise ERPs (SAP S/4HANA, ServiceNow CMDB) via streaming Kafka change data capture (CDC) pipelines.

---

## 2. Security & Compliance Roadmap

1. **Confidential Computing (AMD SEV-SNP / Intel TDX)**: Host the agent runtime inside hardware-isolated confidential virtual machines to protect proprietary prompt queries.
2. **Post-Quantum Cryptography (PQC)**: Upgrade document signature verification to NIST-standardized Kyber/Dilithium algorithms.
3. **Automated Continuous RAG Drift Detection**: Implement automated daily drift detection evaluating embedding cosine shifts as new supplier contracts are ingested.
