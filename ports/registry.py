"""Dependency Injection Registry for hexagonal port adapters.

Instantiates and provides concrete adapter singletons based on config.json.
"""

from __future__ import annotations

from typing import Optional
from ports.base import VectorStorePort, GraphStorePort, LLMProviderPort
from ports.vector_store.chromadb_adapter import ChromaDBAdapter
from ports.graph_store.networkx_adapter import NetworkXAdapter
from ports.llm_provider.openrouter_adapter import OpenRouterAdapter
from utils.config import load_config


class AdapterRegistry:
    """Manages lifecycle and access to port adapter instances."""

    _vector_store: Optional[VectorStorePort] = None
    _graph_store: Optional[GraphStorePort] = None
    _llm_provider: Optional[LLMProviderPort] = None

    @classmethod
    def get_vector_store(cls, force_new: bool = False) -> VectorStorePort:
        if cls._vector_store is None or force_new:
            cfg = load_config()
            adapter_type = cfg.get("ports", {}).get("vector_store", "chromadb")
            if adapter_type == "chromadb":
                cls._vector_store = ChromaDBAdapter()
            else:
                cls._vector_store = ChromaDBAdapter()
        return cls._vector_store

    @classmethod
    def get_graph_store(cls, force_new: bool = False) -> GraphStorePort:
        if cls._graph_store is None or force_new:
            cfg = load_config()
            adapter_type = cfg.get("ports", {}).get("graph_store", "networkx")
            if adapter_type == "networkx":
                cls._graph_store = NetworkXAdapter()
            else:
                cls._graph_store = NetworkXAdapter()
        return cls._graph_store

    @classmethod
    def get_llm_provider(cls, force_new: bool = False) -> LLMProviderPort:
        if cls._llm_provider is None or force_new:
            cfg = load_config()
            adapter_type = cfg.get("ports", {}).get("llm_provider", "openrouter")
            if adapter_type == "openrouter":
                cls._llm_provider = OpenRouterAdapter()
            else:
                cls._llm_provider = OpenRouterAdapter()
        return cls._llm_provider
