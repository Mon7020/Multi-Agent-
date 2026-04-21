from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class VectorSearchRequest:
    query: str
    top_k: int = 3
    query_embedding: Optional[List[float]] = None
    metadata_filter: Optional[Dict[str, Any]] = None
    include: List[str] = field(default_factory=lambda: ["documents", "metadatas", "distances"])


@dataclass
class VectorSearchResult:
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    id: Optional[str] = None


@dataclass(frozen=True)
class VectorStoreCapabilities:
    backend_name: str
    supports_metadata_filter: bool = False
    supports_tenant_isolation: bool = False
    supports_hybrid_search: bool = False
    supports_upsert: bool = False
    supports_delete: bool = False
    notes: str = ""


class VectorStoreBackend(Protocol):
    def search(self, request: VectorSearchRequest) -> List[VectorSearchResult]:
        ...

    def get_capabilities(self) -> VectorStoreCapabilities:
        ...
