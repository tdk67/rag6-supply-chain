"""Hexagonal port interfaces (abstract contracts) for external services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VectorChunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class VectorSearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    metadata: Dict[str, Any]
    score: float


class VectorStorePort(ABC):
    """Abstract port for vector database storage and similarity retrieval."""

    @abstractmethod
    def upsert_chunks(self, collection_name: str, chunks: List[VectorChunk]) -> int:
        """Upsert a list of chunks into the designated collection."""
        pass

    @abstractmethod
    def query(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """Query top_k similar chunks matching optional metadata filter."""
        pass

    @abstractmethod
    def deprecate_by_doc_id(self, doc_id: str) -> int:
        """Mark all chunks belonging to doc_id as inactive/deprecated."""
        pass

    @abstractmethod
    def get_collection_stats(self) -> Dict[str, int]:
        """Return total chunks per collection."""
        pass


class GraphStorePort(ABC):
    """Abstract port for knowledge graph traversal and querying."""

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve node attributes by ID."""
        pass

    @abstractmethod
    def find_nodes(self, label: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Find all nodes with given label matching attribute filters."""
        pass

    @abstractmethod
    def get_neighbors(
        self, node_id: str, direction: str = "both", relation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve neighboring nodes connected via specified relationship."""
        pass

    @abstractmethod
    def execute_traversal(self, start_label: str, relations: List[str], target_label: str) -> List[Dict[str, Any]]:
        """Execute a multi-hop traversal pattern."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        """Return graph node and edge counts."""
        pass


class LLMProviderPort(ABC):
    """Abstract port for Large Language Model generation."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a single completion."""
        pass

    @abstractmethod
    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Execute a chat completion."""
        pass
