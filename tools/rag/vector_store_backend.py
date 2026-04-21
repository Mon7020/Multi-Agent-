from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

ScalarMetadataValue = str | int | float | bool


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


def build_vector_metadata_filter(retrieval_policy: Optional[Dict[str, Any]]) -> Optional[Dict[str, ScalarMetadataValue]]:
    if not isinstance(retrieval_policy, dict):
        return None

    metadata_filter: Dict[str, ScalarMetadataValue] = {}
    tenant_id = str(retrieval_policy.get("tenant_id") or "").strip()
    if tenant_id and tenant_id != "default":
        metadata_filter["tenant_id"] = tenant_id

    explicit_filter = retrieval_policy.get("vector_metadata_filter")
    if isinstance(explicit_filter, dict):
        for key, value in explicit_filter.items():
            if isinstance(key, str) and key and _is_scalar_metadata_value(value):
                metadata_filter[key] = value

    return metadata_filter or None


def metadata_matches_filter(
    metadata: Optional[Dict[str, Any]],
    metadata_filter: Optional[Dict[str, ScalarMetadataValue]],
) -> bool:
    if not metadata_filter:
        return True
    if not isinstance(metadata, dict):
        return False

    for key, expected in metadata_filter.items():
        if metadata.get(key) != expected:
            return False
    return True


def _is_scalar_metadata_value(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) and value is not None
