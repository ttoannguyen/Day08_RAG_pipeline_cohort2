"""
Task 5 — Semantic Search Module.

Tìm kiếm ngữ nghĩa (dense retrieval) trên vector store đã index ở Task 4.
"""

from src.task4_chunking_indexing import (
    CHROMA_DIR,
    COLLECTION_NAME,
    VECTOR_STORE,
    embed_query,
)


def _search_chromadb(query_embedding: list[float], top_k: int) -> list[dict]:
    import chromadb

    if not CHROMA_DIR.exists():
        return []

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output: list[dict] = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        if not doc:
            continue
        meta = meta or {}
        output.append(
            {
                "content": doc,
                "score": 1.0 - float(dist),
                "metadata": {
                    "source": meta.get("source", ""),
                    "doc_type": meta.get("type", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                },
            }
        )

    output.sort(key=lambda item: item["score"], reverse=True)
    return output


def _search_weaviate(query_embedding: list[float], top_k: int) -> list[dict]:
    import os

    import weaviate
    from weaviate.classes.query import MetadataQuery

    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")

    if url and api_key:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=url,
            auth_credentials=weaviate.auth.AuthApiKey(api_key),
        )
    else:
        client = weaviate.connect_to_local()

    try:
        collection = client.collections.get(COLLECTION_NAME)
        response = collection.query.near_vector(
            near_vector=query_embedding,
            limit=top_k,
            return_metadata=MetadataQuery(distance=True),
        )

        output: list[dict] = []
        for obj in response.objects:
            props = obj.properties or {}
            distance = obj.metadata.distance if obj.metadata else 0.0
            output.append(
                {
                    "content": props.get("content", ""),
                    "score": 1.0 - float(distance),
                    "metadata": {
                        "source": props.get("source", ""),
                        "doc_type": props.get("doc_type", ""),
                        "chunk_index": props.get("chunk_index", 0),
                    },
                }
            )
        output.sort(key=lambda item: item["score"], reverse=True)
        return output
    finally:
        client.close()


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,
            'metadata': dict
        }
        Sorted by score descending.
    """
    if not query.strip() or top_k <= 0:
        return []

    query_embedding = embed_query(query)

    if VECTOR_STORE == "weaviate":
        try:
            return _search_weaviate(query_embedding, top_k)
        except Exception:
            pass

    return _search_chromadb(query_embedding, top_k)


if __name__ == "__main__":
    results = semantic_search("hình phạt cho tội tàng trữ ma tuý", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
