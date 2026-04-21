from tools.rag.vector_store_backend import (
    VectorSearchRequest,
    VectorStoreCapabilities,
)
from tools.rag.chroma_backend import ChromaVectorStoreBackend


class FakeEmbeddings:
    def __init__(self):
        self.queries = []

    def embed_query(self, query):
        self.queries.append(query)
        return [0.1, 0.2, 0.3]


class FakeCollection:
    def __init__(self, results=None):
        self.results = results or {
            "documents": [["doc text"]],
            "metadatas": [[{"source": "unit"}]],
            "distances": [[0.12]],
            "ids": [["doc-1"]],
        }
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        return self.results


def test_vector_store_contract_exposes_production_capabilities():
    request = VectorSearchRequest(
        query="refund policy",
        top_k=3,
        query_embedding=[0.4, 0.5],
        metadata_filter={"tenant_id": "tenant-a"},
    )
    capabilities = VectorStoreCapabilities(
        backend_name="chroma",
        supports_metadata_filter=True,
        supports_upsert=True,
        supports_delete=True,
    )

    assert request.query == "refund policy"
    assert request.top_k == 3
    assert request.metadata_filter == {"tenant_id": "tenant-a"}
    assert capabilities.backend_name == "chroma"
    assert capabilities.supports_metadata_filter is True
    assert capabilities.supports_tenant_isolation is False


def test_chroma_backend_search_passes_embedding_and_filter_to_collection():
    collection = FakeCollection()
    embeddings = FakeEmbeddings()
    backend = ChromaVectorStoreBackend(collection=collection, embeddings=embeddings)

    results = backend.search(
        VectorSearchRequest(
            query="hello",
            top_k=2,
            metadata_filter={"tenant_id": "tenant-a"},
        )
    )

    assert embeddings.queries == ["hello"]
    assert collection.calls == [
        {
            "query_embeddings": [[0.1, 0.2, 0.3]],
            "n_results": 2,
            "include": ["documents", "metadatas", "distances"],
            "where": {"tenant_id": "tenant-a"},
        }
    ]
    assert len(results) == 1
    assert results[0].content == "doc text"
    assert results[0].metadata == {"source": "unit"}
    assert results[0].score == 0.12
    assert results[0].id == "doc-1"


def test_chroma_backend_search_returns_empty_when_unavailable():
    backend = ChromaVectorStoreBackend(
        collection=None,
        embeddings=FakeEmbeddings(),
        available=False,
    )

    assert backend.search(VectorSearchRequest(query="hello", top_k=2)) == []
